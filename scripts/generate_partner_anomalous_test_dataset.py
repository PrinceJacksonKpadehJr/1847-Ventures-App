from __future__ import annotations

from datetime import date
from pathlib import Path
import random
import sys

from openpyxl import Workbook

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_partner_test_dataset import build_farmer_profiles, build_annual_rows, write_sheet


MISSING_TOKENS = [None, "", "N/A", "null", "-"]
DATE_PATTERNS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%Y/%m/%d",
    "%d %b %Y",
]


def _inject_master_anomalies(farmers: list[dict[str, object]]) -> None:
    random.seed(20260509)
    count = len(farmers)
    sample_ids = random.sample(range(count), k=max(6, count // 4))

    for idx in sample_ids[:3]:
        farmers[idx]["gps_latitude"] = random.choice(MISSING_TOKENS)
    for idx in sample_ids[3:6]:
        farmers[idx]["gps_longitude"] = random.choice(MISSING_TOKENS)

    if count >= 4:
        farmers[1]["size_in_hectares"] = 120.5
        farmers[2]["shade_tree_cover_pct"] = 99
        farmers[3]["cocoa_composition_pct"] = 5
        farmers[3]["food_crop_composition_pct"] = 95


def _inject_performance_anomalies(rows: list[dict[str, object]]) -> dict[str, int]:
    random.seed(707)
    metrics = {
        "missing_values": 0,
        "outliers": 0,
        "mixed_dates": 0,
    }

    row_count = len(rows)
    if row_count == 0:
        return metrics

    outlier_indices = set(random.sample(range(row_count), k=max(12, row_count // 12)))
    missing_indices = set(random.sample(range(row_count), k=max(24, row_count // 8)))
    mixed_date_indices = set(random.sample(range(row_count), k=max(30, row_count // 6)))

    for i, row in enumerate(rows):
        if i in outlier_indices:
            outlier_type = random.choice(["yield_high", "yield_low", "revenue_spike", "emissions_spike", "negative_income"])
            if outlier_type == "yield_high":
                row["yield_kg"] = round(float(row["yield_kg"]) * random.uniform(3.2, 5.5), 1)
                row["yield_per_hectare"] = round(float(row["yield_per_hectare"]) * random.uniform(3.0, 4.8), 2)
            elif outlier_type == "yield_low":
                row["yield_kg"] = round(float(row["yield_kg"]) * random.uniform(0.03, 0.18), 1)
                row["yield_per_hectare"] = round(float(row["yield_per_hectare"]) * random.uniform(0.05, 0.2), 2)
            elif outlier_type == "revenue_spike":
                row["revenue_usd"] = round(float(row["revenue_usd"]) * random.uniform(4.0, 8.0), 2)
            elif outlier_type == "emissions_spike":
                row["emissions_co2e_kg"] = round(float(row["emissions_co2e_kg"]) * random.uniform(4.5, 9.0), 2)
                row["carbon_balance_co2e_kg"] = round(float(row["emissions_co2e_kg"]) - float(row.get("carbon_removals_co2e_kg") or 0), 2)
            elif outlier_type == "negative_income":
                row["operating_cost_usd"] = round(float(row["revenue_usd"]) * random.uniform(1.2, 1.8), 2)
                row["net_income_usd"] = round(float(row["revenue_usd"]) - float(row["operating_cost_usd"]), 2)

            row["anomaly_tag"] = f"outlier:{outlier_type}"
            metrics["outliers"] += 1

        if i in missing_indices:
            missing_fields = random.sample(
                [
                    "fertilizer_bags",
                    "risk_score",
                    "esg_score",
                    "verification_state",
                    "photos_complete",
                    "yield_kg",
                    "revenue_usd",
                    "emissions_co2e_kg",
                ],
                k=random.randint(1, 3),
            )
            for field in missing_fields:
                row[field] = random.choice(MISSING_TOKENS)
                metrics["missing_values"] += 1

            current_tag = row.get("anomaly_tag")
            row["anomaly_tag"] = f"{current_tag}|missing" if current_tag else "missing"

        if i in mixed_date_indices:
            src = str(row["harvest_date"])
            parsed = date.fromisoformat(src)
            pattern = random.choice(DATE_PATTERNS)
            row["harvest_date"] = parsed.strftime(pattern)
            metrics["mixed_dates"] += 1

            current_tag = row.get("anomaly_tag")
            row["anomaly_tag"] = f"{current_tag}|mixed_date" if current_tag else "mixed_date"

        if "anomaly_tag" not in row:
            row["anomaly_tag"] = "none"

    return metrics


def main() -> None:
    output_path = Path("media/investor_uploads/2026/partner_dashboard_farmer_test_dataset_2026_anomalies.xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    farmers = build_farmer_profiles()
    annual_rows = build_annual_rows(farmers)

    _inject_master_anomalies(farmers)
    stats = _inject_performance_anomalies(annual_rows)

    workbook = Workbook()
    workbook.remove(workbook.active)

    write_sheet(workbook, "farmers_master", farmers)
    write_sheet(workbook, "annual_performance", annual_rows)

    summary = workbook.create_sheet(title="README")
    summary.append(["Dataset", "Partner Dashboard Farmer Test Dataset (Anomalous)"])
    summary.append(["Generated On", date.today().isoformat()])
    summary.append(["Farmers", len(farmers)])
    summary.append(["Annual Records", len(annual_rows)])
    summary.append(["Missing Values Injected", stats["missing_values"]])
    summary.append(["Outlier Rows Injected", stats["outliers"]])
    summary.append(["Mixed-Date Rows Injected", stats["mixed_dates"]])
    summary.append(["Notes", "Contains deliberate data quality issues for stress-testing cleaning and anomaly detection."])

    workbook.save(output_path)

    print(f"Created: {output_path}")
    print(f"Farmers: {len(farmers)}")
    print(f"Annual rows: {len(annual_rows)}")
    print(f"Anomalies: missing={stats['missing_values']}, outliers={stats['outliers']}, mixed_dates={stats['mixed_dates']}")


if __name__ == "__main__":
    main()
