from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from django.db.models import Case, F, FloatField, Sum, Value, When
from django.db.models.functions import Coalesce

from .models import Farm, Harvest, Investment


COCOA_PRICE_PER_KG = 2.65
FERTILIZER_COST_PROXY = {
    "none": 0,
    "1-2": 110,
    "3-5": 275,
    "5+": 460,
}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    token = str(value).strip().replace(",", "")
    if token.startswith("$"):
        token = token[1:]
    if not token:
        return None
    try:
        return float(token)
    except (TypeError, ValueError):
        return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _column_names(schema: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("column", "")).strip() for item in schema]


def _find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]

    for column in columns:
        token = column.lower()
        if any(candidate in token for candidate in candidates):
            return column
    return None


def _detect_model_columns(schema: list[dict[str, Any]]) -> dict[str, str | None]:
    columns = _column_names(schema)
    return {
        "farm": _find_column(columns, ("farm", "farm_name", "farm_id")),
        "farmer": _find_column(columns, ("farmer", "farmer_name", "owner", "producer")),
        "location": _find_column(columns, ("location", "region", "district", "community", "area")),
        "time": _find_column(columns, ("date", "harvest_date", "month", "year", "period", "timestamp")),
        "yield": _find_column(columns, ("yield", "yield_kg", "production", "tons_produced", "quantity")),
        "revenue": _find_column(columns, ("revenue", "income", "sales", "amount", "value")),
        "emissions": _find_column(columns, ("emission", "co2", "co2e", "ghg", "carbon")),
        "hectares": _find_column(columns, ("hectare", "size_in_hectares", "farm_size", "land_size", "area_ha")),
    }


def _relation_confidence(rows: list[dict[str, Any]], column: str | None, reference_values: set[str]) -> dict[str, Any]:
    if not column or not rows:
        return {"coverage": 0.0, "matched_rows": 0, "row_count": len(rows), "confidence": "low"}

    row_count = len(rows)
    matched_rows = 0
    for row in rows:
        token = _normalize_text(row.get(column))
        if token and token in reference_values:
            matched_rows += 1

    coverage = round(matched_rows / row_count, 4) if row_count else 0.0
    if coverage >= 0.7:
        confidence = "high"
    elif coverage >= 0.35:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "coverage": coverage,
        "matched_rows": matched_rows,
        "row_count": row_count,
        "confidence": confidence,
    }


def _build_relationships(rows: list[dict[str, Any]], column_map: dict[str, str | None], farms: list[Farm]) -> list[dict[str, Any]]:
    farm_names = {_normalize_text(farm.name) for farm in farms if farm.name}
    owner_usernames = {_normalize_text(farm.owner.username) for farm in farms if getattr(farm, "owner", None)}
    locations = {_normalize_text(farm.location) for farm in farms if farm.location}

    relationships = []

    farm_rel = _relation_confidence(rows, column_map["farm"], farm_names)
    relationships.append(
        {
            "from_dataset": column_map["farm"] or "(not detected)",
            "to_model": "Farm.name",
            "entity": "farm",
            **farm_rel,
        }
    )

    farmer_rel = _relation_confidence(rows, column_map["farmer"], owner_usernames)
    relationships.append(
        {
            "from_dataset": column_map["farmer"] or "(not detected)",
            "to_model": "Farmer.username",
            "entity": "farmer",
            **farmer_rel,
        }
    )

    location_rel = _relation_confidence(rows, column_map["location"], locations)
    relationships.append(
        {
            "from_dataset": column_map["location"] or "(not detected)",
            "to_model": "Farm.location",
            "entity": "location",
            **location_rel,
        }
    )

    return relationships


def _classify_semantic_tables(column_map: dict[str, str | None]) -> dict[str, list[dict[str, Any]]]:
    fact_tables = []
    dimension_tables = []

    has_production = bool(column_map["yield"])
    has_emissions = bool(column_map["emissions"])
    has_revenue = bool(column_map["revenue"])

    if has_production:
        fact_tables.append(
            {
                "name": "fact_production",
                "grain": "farm x time",
                "measures": [column_map["yield"], column_map["hectares"]],
            }
        )
    if has_emissions:
        fact_tables.append(
            {
                "name": "fact_emissions",
                "grain": "farm x time",
                "measures": [column_map["emissions"]],
            }
        )
    if has_revenue:
        fact_tables.append(
            {
                "name": "fact_transactions",
                "grain": "farm x time",
                "measures": [column_map["revenue"]],
            }
        )

    dimension_tables.extend(
        [
            {"name": "dim_farmer", "keys": [column_map["farmer"], column_map["farm"]]},
            {"name": "dim_location", "keys": [column_map["location"]]},
            {"name": "dim_time", "keys": [column_map["time"]]},
        ]
    )

    for table in fact_tables:
        table["measures"] = [item for item in table["measures"] if item]

    for table in dimension_tables:
        table["keys"] = [item for item in table["keys"] if item]

    return {"fact_tables": fact_tables, "dimension_tables": dimension_tables}


def _safe_divide(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator


def _farm_operating_cost_proxy(sheet2, hectares: float) -> float:
    if not sheet2:
        return hectares * 320

    operating_cost = hectares * 320
    operating_cost += FERTILIZER_COST_PROXY.get(sheet2.fertilizer_bag_range, 0)
    if sheet2.fertilizer_application == "hand":
        operating_cost += 45
    elif sheet2.fertilizer_application == "machine":
        operating_cost += 95
    if sheet2.received_training == "yes":
        operating_cost += 20
    return operating_cost


def _farm_emissions_proxy(sheet1, sheet2) -> float:
    emissions = 140.0
    if sheet2:
        if sheet2.fertilizer_bag_range == "1-2":
            emissions += 220
        elif sheet2.fertilizer_bag_range == "3-5":
            emissions += 520
        elif sheet2.fertilizer_bag_range == "5+":
            emissions += 890

        if sheet2.burns_farm_waste == "sometimes":
            emissions += 130
        elif sheet2.burns_farm_waste == "often":
            emissions += 280

        if sheet2.fertilizer_application == "machine":
            emissions += 60
        if sheet2.cocoa_tree_age == "old":
            emissions += 50

    if sheet1 and sheet1.land_ownership in ["rented", "community"]:
        emissions += 45
    return emissions


def _farm_deforestation_risk_proxy(sheet1, sheet2) -> float:
    risk = 18.0
    if sheet1:
        if not sheet1.gps_captured:
            risk += 12
        if sheet1.land_ownership in ["rented", "community"]:
            risk += 15

    if sheet2:
        if sheet2.has_shade_trees == "none":
            risk += 18
        if sheet2.burns_farm_waste == "sometimes":
            risk += 14
        elif sheet2.burns_farm_waste == "often":
            risk += 28
        if sheet2.practices_agroforestry != "yes":
            risk += 10

    return min(100.0, max(0.0, risk))


def _practice_segment(sheet2) -> str:
    if not sheet2:
        return "No assessment"
    if sheet2.practices_agroforestry == "yes":
        return "Agroforestry"
    if sheet2.has_shade_trees in ["few", "many"]:
        return "Shade trees"
    if sheet2.burns_farm_waste in ["sometimes", "often"]:
        return "Waste burning"
    return "Conventional"


def _build_cross_analysis(dataset_rows: list[dict[str, Any]], column_map: dict[str, str | None], farms: list[Farm]) -> dict[str, Any]:
    farm_by_name = {}
    farm_by_owner = {}
    farm_by_location = {}

    for farm in farms:
        farm_by_name[_normalize_text(farm.name)] = farm
        farm_by_owner[_normalize_text(getattr(farm.owner, "username", ""))] = farm
        farm_by_location[_normalize_text(farm.location)] = farm
        sheet1 = getattr(farm.owner, "assessment_sheet1", None)
        if sheet1 and sheet1.location_name:
            farm_by_location[_normalize_text(sheet1.location_name)] = farm

    yield_vs_emissions = []
    profitability_by_practice = defaultdict(list)
    risk_by_region = defaultdict(list)
    matched_rows = 0

    for row in dataset_rows:
        farm = None
        if column_map.get("farm"):
            farm = farm_by_name.get(_normalize_text(row.get(column_map["farm"])))
        if not farm and column_map.get("farmer"):
            farm = farm_by_owner.get(_normalize_text(row.get(column_map["farmer"])))
        if not farm and column_map.get("location"):
            farm = farm_by_location.get(_normalize_text(row.get(column_map["location"])))
        if not farm:
            continue

        matched_rows += 1
        sheet1 = getattr(farm.owner, "assessment_sheet1", None)
        sheet2 = getattr(farm.owner, "assessment_sheet2", None)

        harvest_kg_platform = float(
            sum((harvest.tons_produced or 0) * 1000 for harvest in farm.harvests.all())
        )
        harvest_kg_dataset = _safe_float(row.get(column_map["yield"])) if column_map.get("yield") else None
        harvest_kg = harvest_kg_dataset if harvest_kg_dataset is not None else harvest_kg_platform

        emissions_dataset = _safe_float(row.get(column_map["emissions"])) if column_map.get("emissions") else None
        emissions = emissions_dataset if emissions_dataset is not None else _farm_emissions_proxy(sheet1, sheet2)

        hectares = float(farm.size_in_hectares or 0)
        revenue = harvest_kg * COCOA_PRICE_PER_KG
        operating_cost = _farm_operating_cost_proxy(sheet2, hectares)
        profitability = revenue - operating_cost

        practice = _practice_segment(sheet2)
        region = (sheet1.location_name if sheet1 and sheet1.location_name else farm.location or "Unmapped")
        risk_score = _farm_deforestation_risk_proxy(sheet1, sheet2)

        yield_vs_emissions.append(
            {
                "farm": farm.name,
                "x": round(harvest_kg, 3),
                "y": round(emissions, 3),
            }
        )
        profitability_by_practice[practice].append(profitability)
        risk_by_region[region].append(risk_score)

    practice_labels = sorted(profitability_by_practice.keys())
    region_labels = sorted(risk_by_region.keys())

    practices_vs_profitability = {
        "labels": practice_labels,
        "values": [
            round(sum(profitability_by_practice[label]) / len(profitability_by_practice[label]), 2)
            for label in practice_labels
        ],
    }

    region_vs_deforestation_risk = {
        "labels": region_labels,
        "values": [
            round(sum(risk_by_region[label]) / len(risk_by_region[label]), 2)
            for label in region_labels
        ],
    }

    return {
        "merge_summary": {
            "linked_rows": matched_rows,
            "input_rows": len(dataset_rows),
            "linked_farms": len({item["farm"] for item in yield_vs_emissions}),
        },
        "yield_vs_emissions": yield_vs_emissions,
        "practices_vs_profitability": practices_vs_profitability,
        "region_vs_deforestation_risk": region_vs_deforestation_risk,
    }


def _sql_computed_metrics(investor) -> dict[str, Any]:
    try:
        farm_ids = list(
            Investment.objects.filter(investor=investor, farm__isnull=False).values_list("farm_id", flat=True)
        )
        farms_qs = Farm.objects.filter(id__in=farm_ids)

        hectares = float(farms_qs.aggregate(value=Coalesce(Sum("size_in_hectares"), 0.0))["value"] or 0.0)

        harvest_kg = float(
            Harvest.objects.filter(farm_id__in=farm_ids)
            .aggregate(value=Coalesce(Sum(F("tons_produced") * Value(1000.0), output_field=FloatField()), 0.0))["value"]
            or 0.0
        )

        revenue_total = harvest_kg * COCOA_PRICE_PER_KG
        farm_count = farms_qs.count()

        emissions_expr = (
            Value(140.0)
            + Case(
                When(owner__assessment_sheet2__fertilizer_bag_range="1-2", then=Value(220.0)),
                When(owner__assessment_sheet2__fertilizer_bag_range="3-5", then=Value(520.0)),
                When(owner__assessment_sheet2__fertilizer_bag_range="5+", then=Value(890.0)),
                default=Value(0.0),
                output_field=FloatField(),
            )
            + Case(
                When(owner__assessment_sheet2__burns_farm_waste="sometimes", then=Value(130.0)),
                When(owner__assessment_sheet2__burns_farm_waste="often", then=Value(280.0)),
                default=Value(0.0),
                output_field=FloatField(),
            )
            + Case(
                When(owner__assessment_sheet2__fertilizer_application="machine", then=Value(60.0)),
                default=Value(0.0),
                output_field=FloatField(),
            )
            + Case(
                When(owner__assessment_sheet2__cocoa_tree_age="old", then=Value(50.0)),
                default=Value(0.0),
                output_field=FloatField(),
            )
            + Case(
                When(owner__assessment_sheet1__land_ownership__in=["rented", "community"], then=Value(45.0)),
                default=Value(0.0),
                output_field=FloatField(),
            )
        )

        emissions_total = float(
            farms_qs.annotate(emission_proxy=emissions_expr).aggregate(value=Coalesce(Sum("emission_proxy"), 0.0))["value"] or 0.0
        )

        return {
            "yield_per_hectare": round(_safe_divide(harvest_kg, hectares), 4),
            "emissions_intensity": round(_safe_divide(emissions_total, harvest_kg), 6),
            "revenue_per_farm": round(_safe_divide(revenue_total, float(farm_count)), 2),
            "sql_inputs": {
                "total_hectares": round(hectares, 2),
                "total_harvest_kg": round(harvest_kg, 2),
                "total_emissions_proxy": round(emissions_total, 2),
                "farm_count": farm_count,
            },
        }
    except Exception as exc:
        return {
            "yield_per_hectare": 0.0,
            "emissions_intensity": 0.0,
            "revenue_per_farm": 0.0,
            "sql_inputs": {
                "total_hectares": 0.0,
                "total_harvest_kg": 0.0,
                "total_emissions_proxy": 0.0,
                "farm_count": 0,
                "fallback_error": str(exc),
            },
        }


def _dax_like_defs(column_map: dict[str, str | None]) -> list[dict[str, str]]:
    yield_column = column_map["yield"] or "yield_kg"
    hectare_column = column_map["hectares"] or "size_in_hectares"
    emissions_column = column_map["emissions"] or "emissions"
    revenue_column = column_map["revenue"] or "revenue"

    return [
        {
            "name": "Yield Per Hectare",
            "expression": f"DIVIDE(SUM({yield_column}), SUM({hectare_column}), 0)",
        },
        {
            "name": "Emissions Intensity",
            "expression": f"DIVIDE(SUM({emissions_column}), SUM({yield_column}), 0)",
        },
        {
            "name": "Revenue Per Farm",
            "expression": f"DIVIDE(SUM({revenue_column}), DISTINCTCOUNT(farm), 0)",
        },
    ]


def build_dynamic_semantic_model(dataset_schema: list[dict[str, Any]], dataset_rows: list[dict[str, Any]], investor) -> dict[str, Any]:
    column_map = _detect_model_columns(dataset_schema)
    farm_ids = list(
        Investment.objects.filter(investor=investor, farm__isnull=False).values_list("farm_id", flat=True)
    )
    farms = list(Farm.objects.filter(id__in=farm_ids).select_related("owner"))

    relationships = _build_relationships(dataset_rows, column_map, farms)
    table_suggestions = _classify_semantic_tables(column_map)

    dominant_keys = Counter()
    for relationship in relationships:
        if relationship["from_dataset"] != "(not detected)":
            dominant_keys[relationship["from_dataset"]] += 1

    return {
        "column_map": column_map,
        "relationships": relationships,
        "table_suggestions": table_suggestions,
        "computed_metrics": _sql_computed_metrics(investor),
        "cross_analysis": _build_cross_analysis(dataset_rows, column_map, farms),
        "dax_like_measures": _dax_like_defs(column_map),
        "recommended_primary_keys": [key for key, _ in dominant_keys.most_common(3)],
    }


# =================================================
# Domain Classification
# =================================================
def detect_dataset_domain(dataset_schema: list[dict[str, Any]], dataset_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Infer the semantic domain (category) of a dataset based on column names, types, and sample values.
    
    Returns:
        {
            "inferred_domain": "agriculture",  # Top confidence domain
            "domain_scores": {
                "agriculture": 0.92,
                "finance": 0.15,
                "hr": 0.05,
                "inventory": 0.08,
                "carbon_esg": 0.35,
                "general": 0.10
            }
        }
    """
    
    # Domain keywords and indicators
    DOMAIN_INDICATORS = {
        "agriculture": {
            "keywords": {
                "yield", "farm", "crop", "harvest", "hectare", "cocoa", "cocoa_beans", 
                "production", "land", "agricultural", "farming", "crops", "planting",
                "tons_produced", "harvest_date", "farm_size", "farmer", "producer"
            },
            "strong_keywords": {"yield", "farm", "harvest", "crop", "hectare", "cocoa"},
            "weight": 1.0,
        },
        "finance": {
            "keywords": {
                "revenue", "profit", "expense", "cost", "income", "sales", "invoice",
                "amount", "price", "payment", "transaction", "financial", "bank",
                "balance", "budget", "expense", "money", "currency", "rate", "fee"
            },
            "strong_keywords": {"revenue", "profit", "expense", "invoice", "amount"},
            "weight": 1.0,
        },
        "hr": {
            "keywords": {
                "employee", "salary", "wage", "department", "hire_date", "position",
                "employee_id", "staff", "team", "manager", "employment", "hr",
                "personnel", "payroll", "benefit", "leave", "role"
            },
            "strong_keywords": {"employee", "salary", "department", "hire_date"},
            "weight": 1.0,
        },
        "inventory": {
            "keywords": {
                "sku", "stock", "warehouse", "inventory", "units", "quantity", "bin",
                "stock_level", "reorder", "supplier", "product", "storage", "shelf",
                "batch", "lot", "part_number", "item_code", "item_id"
            },
            "strong_keywords": {"sku", "stock", "warehouse", "inventory", "units"},
            "weight": 1.0,
        },
        "carbon_esg": {
            "keywords": {
                "emission", "co2", "co2e", "carbon", "ghg", "sustainability",
                "emissions", "carbon_footprint", "scope", "sustainability", "esg",
                "environmental", "baseline", "reduction", "target", "offset"
            },
            "strong_keywords": {"emission", "co2", "carbon", "ghg", "emissions"},
            "weight": 1.0,
        },
    }
    
    columns = _column_names(dataset_schema)
    column_types = {}
    for col_info in dataset_schema:
        col_name = str(col_info.get("column", "")).strip()
        col_type = str(col_info.get("type", "string")).strip().lower()
        if col_name:
            column_types[col_name.lower()] = col_type
    
    # Calculate scores for each domain
    domain_scores = {}
    
    for domain, indicators in DOMAIN_INDICATORS.items():
        score = 0.0
        keywords_found = set()
        strong_keywords_found = set()
        
        # Check column names against keywords
        for col in columns:
            col_normalized = col.lower()
            
            # Check for strong keywords (higher weight)
            for strong_kw in indicators["strong_keywords"]:
                if strong_kw in col_normalized or col_normalized in strong_kw:
                    strong_keywords_found.add(strong_kw)
            
            # Check for regular keywords
            for keyword in indicators["keywords"]:
                if keyword in col_normalized or col_normalized in keyword:
                    keywords_found.add(keyword)
        
        # Score calculation based on matches
        # Strong keywords: 0.25 each (up to 1.0)
        score += min(0.25 * len(strong_keywords_found), 1.0)
        
        # Regular keywords: 0.05 each (up to 0.5)
        score += min(0.05 * len(keywords_found), 0.5)
        
        # Boost if multiple indicators found
        total_indicators = len(strong_keywords_found) + len(keywords_found)
        if total_indicators >= 3:
            score = min(score * 1.2, 1.0)
        elif total_indicators >= 2:
            score = min(score * 1.1, 1.0)
        
        domain_scores[domain] = round(score, 3)
    
    # Ensure general domain always has a baseline
    domain_scores["general"] = round(0.1 if domain_scores.get("agriculture", 0) < 0.5 else 0.0, 3)
    
    # Find top domain
    inferred_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
    if domain_scores[inferred_domain] < 0.1:
        inferred_domain = "general"
    
    return {
        "inferred_domain": inferred_domain,
        "domain_scores": domain_scores,
        "confidence": round(domain_scores[inferred_domain], 3),
    }
