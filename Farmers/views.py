from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from collections import defaultdict, Counter
from datetime import datetime
from django.db.models import Q, Max
import statistics
import json
import re
import secrets
import io
import os
import uuid
from urllib import parse, request, error
from .models import Message, Notification
from .serializers import MessageSerializer
from Farmers.decorators import approved_user_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import SetPasswordForm
from django.urls import Resolver404, resolve, reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction
from Farmers.models import UserProfile, AdminNotification, ContactSubmission, FarmerRegistrationRequest, PasswordResetRequest, FarmerDeletionRequest, FarmAssessmentSheet1, FarmAssessmentSheet2, FarmAssessmentSheet3
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.core.files.base import ContentFile
from django.utils.dateparse import parse_date
from PIL import Image, ImageOps
from .forms import FarmerCreateByAgentForm, CreateUserForm, FarmerRegistrationRequestForm, PasswordResetRequestForm, HomeContactForm, FarmAssessmentSheet1Form, FarmAssessmentSheet2Form, FarmAssessmentSheet3Form, InvestorDatasetUploadForm, FarmerActivitySubmissionForm
from .import_pipeline import parse_and_clean_dataset, DatasetImportError
from .semantic_modeling import build_dynamic_semantic_model, detect_dataset_domain
from .data_prep import DataPrepHistory, ColumnOperations, RowOperations, LivePreviewGenerator







from .models import Farmer, Farm, Harvest, Investment, FarmActivity, Announcement
from .models import InvestorDatasetImport, InvestorDatasetRow
from .models import DatasetAuditLog
from .serializers import (
    FarmerSerializer,
    FarmSerializer,
    HarvestSerializer,
    InvestmentSerializer,
    FarmActivitySerializer,
    AnnouncementSerializer,
    FarmerRegistrationSerializer
)


COCOA_PRICE_PER_KG = 2.65
ANALYTICS_CACHE_TTL_SECONDS = 300
DASHBOARD_CACHE_TTL_SECONDS = 120
AUDIT_LOG_PAGE_SIZE = 50
ROW_BULK_CREATE_BATCH_SIZE = 1000
FARM_SIZE_HECTARE_PROXY = {
    "small": 1.2,
    "medium": 2.8,
    "large": 5.6,
}
HARVEST_BAG_KG_PROXY = {
    "0-5": 160,
    "6-10": 512,
    "11-20": 992,
    "21+": 1536,
}
FERTILIZER_COST_PROXY = {
    "none": 0,
    "1-2": 110,
    "3-5": 275,
    "5+": 460,
}
FERTILIZER_EMISSIONS_PROXY = {
    "none": 0,
    "1-2": 220,
    "3-5": 520,
    "5+": 890,
}
SHADE_REMOVAL_PROXY = {
    "none": 0,
    "few": 180,
    "many": 420,
}
HARVEST_TREND_SCORE = {
    "less": -1,
    "same": 0,
    "more": 1,
}
POWER_BI_TOKEN_CACHE_TTL_SECONDS = 3300
APPROVED_SUPERUSER_PARTNER_ROUTE_PREFIXES = ("partner_",)
APPROVED_SUPERUSER_PARTNER_PATH_PREFIXES = ("/api/farmers/partner/",)
SUPERUSER_SCOPE_PREFIXES = {
    "admin": ("/api/farmers/admin/", "/api/farmers/governance/"),
    "partner": ("/api/farmers/partner/",),
    "agent": ("/api/farmers/agent/",),
    "farmer": ("/api/farmers/farmer/",),
    "messages": ("/api/farmers/messages/",),
    "django_admin": ("/admin/",),
}

ENTERPRISE_WORKSPACE_PAGES = [
    {"id": "investor-dashboard", "label": "Investor Dashboard"},
    {"id": "external-dataset-analysis", "label": "External Dataset Analysis"},
    {"id": "field-agent-data-center", "label": "Field Agent Data Center"},
    {"id": "ai-insights-recommendations", "label": "AI Insights & Recommendations"},
    {"id": "farm-portfolio-intelligence", "label": "Farm Portfolio Intelligence"},
    {"id": "predictive-analytics", "label": "Predictive Analytics"},
    {"id": "esg-carbon-monitoring", "label": "ESG / Carbon Monitoring"},
    {"id": "visualization-studio", "label": "Visualization Studio"},
    {"id": "saved-reports-exports", "label": "Saved Reports & Exports"},
    {"id": "admin-data-governance", "label": "Admin & Data Governance"},
]

FIELD_AGENT_FORM_SCHEMA = [
    {"header": "submission_id", "description": "Unique form submission identifier."},
    {"header": "submission_date", "description": "Date/time when the field record was submitted."},
    {"header": "agent_id", "description": "Field agent identifier."},
    {"header": "agent_name", "description": "Field agent full name."},
    {"header": "farmer_id", "description": "Unique farmer identifier."},
    {"header": "farmer_name", "description": "Farmer full name."},
    {"header": "phone_number", "description": "Farmer phone contact."},
    {"header": "farm_location", "description": "Farm location string (region/district/community)."},
    {"header": "gps_latitude", "description": "Farm GPS latitude coordinate."},
    {"header": "gps_longitude", "description": "Farm GPS longitude coordinate."},
    {"header": "crop_type", "description": "Primary crop type captured by the field agent."},
    {"header": "field_size_acres", "description": "Farm size captured in acres."},
    {"header": "planting_date", "description": "Planting date for the current crop cycle."},
    {"header": "current_stage", "description": "Current crop growth stage at collection time."},
    {"header": "issues_observed", "description": "Observed issues (disease, pests, drought, etc.)."},
    {"header": "inputs_used", "description": "Farm inputs used (fertilizer, chemicals, seed, labor)."},
    {"header": "expected_harvest_date", "description": "Expected harvest date."},
    {"header": "yield_estimate", "description": "Yield estimate supplied by the field team."},
    {"header": "agent_notes", "description": "Field agent observational notes."},
    {"header": "photo_url", "description": "Evidence photo URL/path for traceability."},
]

VISUALIZATION_CATALOG = [
    "bar_chart", "line_chart", "area_chart", "pie_chart", "histogram", "scatter_plot", "bubble_chart", "heatmap",
    "kpi_cards", "pivot_table", "maps", "treemap", "waterfall_chart", "funnel_chart", "decomposition_tree",
    "radar_chart", "sankey_diagram", "box_plot", "correlation_matrix", "timeline_chart",
]


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def _safe_divide(numerator, denominator):
    if not denominator:
        return 0
    return numerator / denominator


def _build_cache_key(prefix, *parts):
    return "|".join([prefix, *[str(part) for part in parts]])


def _schema_column_names(schema):
    names = []
    for col in schema or []:
        if not isinstance(col, dict):
            continue
        candidate = col.get("name") or col.get("column")
        if candidate:
            names.append(candidate)
    return names


def _user_has_role(user, allowed_roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, "profile"):
        return False
    return user.profile.role in allowed_roles


def _field_agent_farmer_queryset(user):
    base_qs = Farmer.objects.filter(profile__role="farmer")
    if user.is_superuser:
        return base_qs
    return base_qs.filter(profile__created_by_agent=user)


def _activity_sort_key(value):
    if value is None:
        return timezone.make_aware(datetime.min)
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def _build_farmer_activity_log(farmer):
    activity_log = [
        {
            "timestamp": farmer.registration_date,
            "title": "Farmer account registered",
            "detail": f"Account created for {farmer.username}.",
            "kind": "account",
        }
    ]

    profile = getattr(farmer, "profile", None)
    if profile and profile.created_by_agent:
        activity_log.append(
            {
                "timestamp": farmer.registration_date,
                "title": "Assigned field agent",
                "detail": f"Created by field agent {profile.created_by_agent.username}.",
                "kind": "assignment",
            }
        )

    sheet1 = getattr(farmer, "assessment_sheet1", None)
    if sheet1:
        activity_log.append(
            {
                "timestamp": sheet1.updated_at or sheet1.created_at,
                "title": "Sheet 1 submitted",
                "detail": f"Profile and location captured for {sheet1.location_name or 'farmer intake'}.",
                "kind": "assessment",
            }
        )

    sheet2 = getattr(farmer, "assessment_sheet2", None)
    if sheet2:
        activity_log.append(
            {
                "timestamp": sheet2.updated_at or sheet2.created_at,
                "title": "Sheet 2 submitted",
                "detail": "Farm assessment details were recorded.",
                "kind": "assessment",
            }
        )

    sheet3 = getattr(farmer, "assessment_sheet3", None)
    if sheet3:
        detail_bits = []
        if sheet3.photos_complete:
            detail_bits.append("photos complete")
        if sheet3.data_validated:
            detail_bits.append("data validated")
        activity_log.append(
            {
                "timestamp": sheet3.updated_at or sheet3.created_at,
                "title": "Sheet 3 submitted",
                "detail": ", ".join(detail_bits) if detail_bits else "Verification evidence captured.",
                "kind": "assessment",
            }
        )

    for item in farmer.activities.all().order_by("-date", "-id"):
        detail_bits = [
            f"Quantity: {item.quantity}" if item.quantity is not None else "",
            f"Inputs: {item.inputs_used}" if item.inputs_used else "",
            f"Additional trees: {item.additional_trees_added}" if item.additional_trees_added else "",
            f"Tool change: {item.tool_changed_from or 'N/A'} -> {item.tool_changed_to}" if item.tool_changed_to else "",
            f"Habit change: {item.habit_changed_from or 'N/A'} -> {item.habit_changed_to}" if item.habit_changed_to else "",
            item.notes or "",
        ]

        status_detail = (
            f"Field verification: {item.get_verification_status_display()} | "
            f"Admin review: {item.get_admin_approval_status_display()}"
        )

        activity_log.append(
            {
                "timestamp": item.verified_at or item.admin_reviewed_at or timezone.make_aware(datetime.combine(item.date, datetime.min.time())),
                "title": f"Farm activity: {item.get_activity_type_display()}",
                "detail": " | ".join(
                    part for part in detail_bits
                    if part
                ) or "Recorded farm activity.",
                "kind": "farm-activity",
                "status": status_detail,
            }
        )

    for item in AdminNotification.objects.filter(related_farmer=farmer).order_by("-created_at")[:20]:
        activity_log.append(
            {
                "timestamp": item.created_at,
                "title": f"Admin notification: {item.get_notification_type_display()}",
                "detail": item.message,
                "kind": "notification",
            }
        )

    return sorted(activity_log, key=lambda item: _activity_sort_key(item.get("timestamp")), reverse=True)


def _log_dataset_audit(actor, action, dataset=None, details=None):
    DatasetAuditLog.objects.create(
        actor=actor,
        dataset=dataset,
        action=action,
        details=details or {},
    )


class PowerBIClientError(Exception):
    pass


def _power_bi_settings_complete():
    required_values = [
        settings.POWER_BI_TENANT_ID,
        settings.POWER_BI_CLIENT_ID,
        settings.POWER_BI_CLIENT_SECRET,
        settings.POWER_BI_WORKSPACE_ID,
        settings.POWER_BI_REPORT_ID,
    ]
    return all(required_values)


class PowerBIService:
    def __init__(self):
        self.tenant_id = settings.POWER_BI_TENANT_ID
        self.client_id = settings.POWER_BI_CLIENT_ID
        self.client_secret = settings.POWER_BI_CLIENT_SECRET
        self.workspace_id = settings.POWER_BI_WORKSPACE_ID
        self.report_id = settings.POWER_BI_REPORT_ID
        self.dataset_id = settings.POWER_BI_DATASET_ID
        self.scope = settings.POWER_BI_SCOPE
        self.resource_url = settings.POWER_BI_RESOURCE_URL.rstrip("/")

    def _request_json(self, method, url, payload=None, headers=None):
        req_headers = headers or {}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = request.Request(url=url, data=data, headers=req_headers, method=method)
        try:
            with request.urlopen(req, timeout=20) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
            raise PowerBIClientError(f"Power BI API request failed ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise PowerBIClientError(f"Power BI API connection failed: {exc.reason}") from exc

    def get_access_token(self):
        cache_key = _build_cache_key("powerbi_access_token", self.tenant_id, self.client_id)
        cached_token = cache.get(cache_key)
        if cached_token:
            return cached_token

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }
        encoded_payload = parse.urlencode(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=encoded_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
            raise PowerBIClientError(f"Power BI auth failed ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise PowerBIClientError(f"Power BI auth connection failed: {exc.reason}") from exc

        token = body.get("access_token")
        if not token:
            raise PowerBIClientError("Power BI auth response did not contain access_token")

        cache.set(cache_key, token, POWER_BI_TOKEN_CACHE_TTL_SECONDS)
        return token

    def get_embed_config(self):
        access_token = self.get_access_token()
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        report_url = (
            f"{self.resource_url}/v1.0/myorg/groups/{self.workspace_id}/reports/{self.report_id}"
        )
        report = self._request_json("GET", report_url, headers=auth_headers)

        generate_token_url = (
            f"{self.resource_url}/v1.0/myorg/groups/{self.workspace_id}/reports/{self.report_id}/GenerateToken"
        )
        embed_token_response = self._request_json(
            "POST",
            generate_token_url,
            payload={"accessLevel": "View"},
            headers=auth_headers,
        )

        embed_token = embed_token_response.get("token")
        if not embed_token:
            raise PowerBIClientError("Power BI embed token response did not contain token")

        dataset_id = self.dataset_id or report.get("datasetId")
        return {
            "reportId": report.get("id", self.report_id),
            "reportName": report.get("name", "Portfolio Intelligence"),
            "embedUrl": report.get("embedUrl"),
            "embedToken": embed_token,
            "datasetId": dataset_id,
        }

    def refresh_dataset(self):
        target_dataset_id = self.dataset_id
        if not target_dataset_id:
            raise PowerBIClientError("POWER_BI_DATASET_ID is not configured")

        access_token = self.get_access_token()
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        refresh_url = (
            f"{self.resource_url}/v1.0/myorg/groups/{self.workspace_id}/datasets/{target_dataset_id}/refreshes"
        )
        response = self._request_json(
            "POST",
            refresh_url,
            payload={"notifyOption": "NoNotification"},
            headers=auth_headers,
        )
        return {
            "status": "submitted",
            "requestId": response.get("requestId") or response.get("id") or "",
            "datasetId": target_dataset_id,
        }


@login_required
def partner_powerbi_embedded(request):
    if not _user_has_role(request.user, {"investor", "analyst", "admin"}):
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/partner_powerbi_embedded.html")


@login_required
def partner_powerbi_embed_config(request):
    if not _user_has_role(request.user, {"investor", "analyst", "admin"}):
        return HttpResponseForbidden("Access Denied")

    if not _power_bi_settings_complete():
        return JsonResponse(
            {
                "ok": False,
                "error": "Power BI is not configured. Set POWER_BI_* environment variables.",
            },
            status=500,
        )

    service = PowerBIService()
    try:
        config = service.get_embed_config()
    except PowerBIClientError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)

    return JsonResponse({"ok": True, "config": config})


@login_required
def partner_powerbi_refresh_dataset(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    if not _user_has_role(request.user, {"analyst", "admin"}):
        return HttpResponseForbidden("Access Denied")

    if not _power_bi_settings_complete() or not settings.POWER_BI_DATASET_ID:
        return JsonResponse(
            {
                "ok": False,
                "error": "Power BI dataset refresh is not configured.",
            },
            status=500,
        )

    service = PowerBIService()
    try:
        refresh_info = service.refresh_dataset()
    except PowerBIClientError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)

    return JsonResponse({"ok": True, "refresh": refresh_info})


def _numeric_histogram(values, max_bins=10):
    if not values:
        return []
    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return [{"label": str(round(min_v, 2)), "count": len(values)}]

    n_bins = min(max_bins, max(2, len(set(values))))
    bin_size = (max_v - min_v) / n_bins
    counts = [0] * n_bins
    for value in values:
        idx = min(int((value - min_v) / bin_size), n_bins - 1)
        counts[idx] += 1

    bins = []
    for i in range(n_bins):
        lo = round(min_v + i * bin_size, 2)
        hi = round(min_v + (i + 1) * bin_size, 2)
        bins.append({"label": f"{lo}-{hi}", "count": counts[i]})
    return bins


def _portfolio_region(farm, sheet1):
    return (sheet1.location_name if sheet1 and sheet1.location_name else farm.location or "Unmapped")


def _most_recent_harvest(sheet3):
    """Return the bag-range string for the most recent year in harvest_history."""
    history = getattr(sheet3, "harvest_history", {}) or {}
    if not history:
        return ""
    return history.get(max(history.keys()), "")


def _harvest_trend_signal(sheet3):
    """Return -1/0/1 comparing most recent vs previous year harvest."""
    history = getattr(sheet3, "harvest_history", {}) or {}
    sorted_years = sorted(history.keys(), reverse=True)
    if len(sorted_years) >= 2:
        recent = HARVEST_BAG_KG_PROXY.get(history[sorted_years[0]], 0)
        prev = HARVEST_BAG_KG_PROXY.get(history[sorted_years[1]], 0)
        if recent > prev:
            return 1
        if recent < prev:
            return -1
    return 0


def _farm_financials(farm, sheet2, harvests):
    hectares = farm.size_in_hectares or FARM_SIZE_HECTARE_PROXY.get(getattr(sheet2, "farm_size_category", ""), 0)
    harvest_kg = sum((harvest.tons_produced or 0) * 1000 for harvest in harvests)
    if not harvest_kg:
        sheet3 = getattr(farm.owner, "assessment_sheet3", None)
        harvest_kg = HARVEST_BAG_KG_PROXY.get(_most_recent_harvest(sheet3), 0)

    revenue = harvest_kg * COCOA_PRICE_PER_KG
    operating_cost = hectares * 320

    if sheet2:
        operating_cost += FERTILIZER_COST_PROXY.get(sheet2.fertilizer_bag_range, 0)
        if sheet2.fertilizer_application == "hand":
            operating_cost += 45
        elif sheet2.fertilizer_application == "machine":
            operating_cost += 95
        if sheet2.received_training == "yes":
            operating_cost += 20

    return hectares, harvest_kg, revenue, operating_cost, revenue - operating_cost


def _farm_carbon_metrics(sheet1, sheet2, sheet3, harvest_kg):
    emissions = 140
    removals = 0

    if sheet2:
        emissions += FERTILIZER_EMISSIONS_PROXY.get(sheet2.fertilizer_bag_range, 0)
        if sheet2.burns_farm_waste == "sometimes":
            emissions += 130
        elif sheet2.burns_farm_waste == "often":
            emissions += 280
        if sheet2.fertilizer_application == "machine":
            emissions += 60
        year_planted = getattr(sheet2, "year_planted", None)
        if year_planted and (datetime.today().year - int(year_planted)) >= 25:
            emissions += 50

        removals += SHADE_REMOVAL_PROXY.get(sheet2.has_shade_trees, 0)
        if sheet2.practices_agroforestry == "yes":
            removals += 260
        if sheet2.plants_trees == "yes":
            removals += 140

    if sheet1 and sheet1.land_ownership in ["rented", "community"]:
        emissions += 45

    if sheet3 and sheet3.data_validated:
        removals += 35

    intensity = _safe_divide(emissions, harvest_kg)
    balance = emissions - removals
    return emissions, removals, intensity, balance


def _farm_risk_and_esg(sheet1, sheet2, sheet3):
    risk = 18
    esg = 45

    if sheet1:
        if sheet1.gps_captured:
            esg += 15
        else:
            risk += 12
        if sheet1.belongs_to_group == "yes":
            esg += 8
        if sheet1.land_ownership in ["rented", "community"]:
            risk += 15

    if sheet2:
        if sheet2.has_shade_trees == "none":
            risk += 18
        elif sheet2.has_shade_trees == "few":
            esg += 6
        elif sheet2.has_shade_trees == "many":
            esg += 12

        if sheet2.burns_farm_waste == "sometimes":
            risk += 14
        elif sheet2.burns_farm_waste == "often":
            risk += 28

        if sheet2.practices_agroforestry == "yes":
            esg += 10
        else:
            risk += 10

        if sheet2.received_training == "yes":
            esg += 10
        else:
            risk += 8

    if sheet3:
        if sheet3.photos_complete:
            esg += 10
        else:
            risk += 10
        if sheet3.data_validated:
            esg += 12
        else:
            risk += 10
        if sheet3.validation_notes:
            risk += 12

    risk = _clamp(risk)
    esg = _clamp(esg - int(risk * 0.18))
    return risk, esg


def _metric_status(value, good_threshold, warning_threshold, inverse=False):
    if inverse:
        if value <= good_threshold:
            return "good"
        if value <= warning_threshold:
            return "warning"
        return "risk"
    if value >= good_threshold:
        return "good"
    if value >= warning_threshold:
        return "warning"
    return "risk"


def _build_partner_dashboard_context(user, selected_region="", selected_size="", selected_certification=""):
    investment_qs = Investment.objects.select_related("farm", "farm__owner")
    farms = list(
        Farm.objects.select_related("owner", "owner__profile")
        .prefetch_related("harvests")
    )
    farmer_ids_with_farms = {farm.owner_id for farm in farms}
    unlinked_farmers = list(
        Farmer.objects.select_related("profile")
        .filter(profile__role="farmer", profile__is_approved=True)
        .exclude(id__in=farmer_ids_with_farms)
    )
    scope_label = "Shared investor team portfolio"

    all_regions_set = {
        _portfolio_region(farm, getattr(farm.owner, "assessment_sheet1", None))
        for farm in farms
    }
    for owner in unlinked_farmers:
        sheet1 = getattr(owner, "assessment_sheet1", None)
        all_regions_set.add(sheet1.location_name if sheet1 and sheet1.location_name else "Unmapped")
    all_regions = sorted(all_regions_set)

    farm_rows = []
    region_rollup = defaultdict(lambda: {
        "farms": 0,
        "hectares": 0.0,
        "yield_kg": 0.0,
        "carbon_balance": 0.0,
        "esg_total": 0.0,
        "risk_farms": 0,
    })
    trend_rollup = defaultdict(lambda: {"yield_kg": 0.0, "emissions": 0.0})

    for farm in farms:
        owner = farm.owner
        sheet1 = getattr(owner, "assessment_sheet1", None)
        sheet2 = getattr(owner, "assessment_sheet2", None)
        sheet3 = getattr(owner, "assessment_sheet3", None)
        region = _portfolio_region(farm, sheet1)
        farm_size = getattr(sheet2, "farm_size_category", "unknown")

        if selected_region and region != selected_region:
            continue
        if selected_size and farm_size != selected_size:
            continue

        harvests = list(farm.harvests.all().order_by("date_of_harvest"))
        hectares, harvest_kg, revenue, operating_cost, net_income = _farm_financials(farm, sheet2, harvests)
        emissions, removals, emissions_intensity, carbon_balance = _farm_carbon_metrics(sheet1, sheet2, sheet3, harvest_kg)
        risk_score, esg_score = _farm_risk_and_esg(sheet1, sheet2, sheet3)
        latest_year = harvests[-1].date_of_harvest.year if harvests else timezone.now().year

        trend_rollup[latest_year]["yield_kg"] += harvest_kg
        trend_rollup[latest_year]["emissions"] += emissions

        farm_investments = [item for item in investment_qs if item.farm_id == farm.id]
        invested_amount = sum(float(item.amount or 0) for item in farm_investments)
        expected_return = 0
        if farm_investments:
            expected_return = sum(float(item.expected_return_percentage or 0) for item in farm_investments) / len(farm_investments)

        verification_state = "Verified" if sheet3 and sheet3.data_validated else "Review"
        traceability_state = "Complete" if sheet1 and sheet1.gps_captured and sheet3 and sheet3.photos_complete else "Partial"
        certification = "certified" if verification_state == "Verified" else "pending"

        if selected_certification and certification != selected_certification:
            continue

        row = {
            "farm_name": farm.name,
            "farmer_name": getattr(sheet1, "full_name", owner.get_full_name() or owner.username),
            "region": region,
            "farm_size": farm_size.title() if farm_size != "unknown" else "Unknown",
            "farm_size_code": farm_size,
            "hectares": round(hectares, 1),
            "yield_kg": round(harvest_kg, 0),
            "yield_per_hectare": round(_safe_divide(harvest_kg, hectares), 1),
            "revenue": round(revenue, 2),
            "operating_cost": round(operating_cost, 2),
            "cost_per_hectare": round(_safe_divide(operating_cost, hectares), 2),
            "net_income": round(net_income, 2),
            "emissions": round(emissions, 1),
            "removals": round(removals, 1),
            "emissions_intensity": round(emissions_intensity, 3),
            "carbon_balance": round(carbon_balance, 1),
            "risk_score": risk_score,
            "esg_score": esg_score,
            "harvest_signal": _harvest_trend_signal(sheet3),
            "verification_state": verification_state,
            "certification": certification,
            "traceability_state": traceability_state,
            "invested_amount": round(invested_amount, 2),
            "expected_return": round(expected_return, 1),
            "has_agroforestry": getattr(sheet2, "practices_agroforestry", "no") == "yes",
            "has_shade": getattr(sheet2, "has_shade_trees", "none") in ["few", "many"],
            "burns_waste": getattr(sheet2, "burns_farm_waste", "never"),
            "detail_anchor": f"farm-{farm.id}",
            "is_high_risk": risk_score >= 65,
            "is_non_compliant": verification_state != "Verified" or risk_score >= 65,
            "time_year": latest_year,
            "input_usage": "fertilizer" if getattr(sheet2, "uses_fertilizer", "no") == "yes" else "no_fertilizer",
            "yield_category": (
                "high" if _safe_divide(harvest_kg, hectares) >= 550
                else "medium" if _safe_divide(harvest_kg, hectares) >= 350
                else "low"
            ),
            "latitude": float(sheet1.latitude) if sheet1 and sheet1.latitude is not None else None,
            "longitude": float(sheet1.longitude) if sheet1 and sheet1.longitude is not None else None,
            "year_planted": getattr(sheet2, "year_planted", None),
        }
        farm_rows.append(row)

        region_rollup[region]["farms"] += 1
        region_rollup[region]["hectares"] += hectares
        region_rollup[region]["yield_kg"] += harvest_kg
        region_rollup[region]["carbon_balance"] += carbon_balance
        region_rollup[region]["esg_total"] += esg_score
        if risk_score >= 65:
            region_rollup[region]["risk_farms"] += 1

    for owner in unlinked_farmers:
        sheet1 = getattr(owner, "assessment_sheet1", None)
        sheet2 = getattr(owner, "assessment_sheet2", None)
        sheet3 = getattr(owner, "assessment_sheet3", None)
        region = sheet1.location_name if sheet1 and sheet1.location_name else "Unmapped"
        farm_size = getattr(sheet2, "farm_size_category", "unknown")

        if selected_region and region != selected_region:
            continue
        if selected_size and farm_size != selected_size:
            continue

        risk_score, esg_score = _farm_risk_and_esg(sheet1, sheet2, sheet3)
        emissions, removals, emissions_intensity, carbon_balance = _farm_carbon_metrics(sheet1, sheet2, sheet3, 0)
        verification_state = "Verified" if sheet3 and sheet3.data_validated else "Review"
        traceability_state = "Complete" if sheet1 and sheet1.gps_captured and sheet3 and sheet3.photos_complete else "Partial"
        certification = "certified" if verification_state == "Verified" else "pending"

        if selected_certification and certification != selected_certification:
            continue

        row = {
            "farm_name": "No farm linked",
            "farmer_name": getattr(sheet1, "full_name", owner.get_full_name() or owner.username),
            "region": region,
            "farm_size": farm_size.title() if farm_size != "unknown" else "Unknown",
            "farm_size_code": farm_size,
            "hectares": 0,
            "yield_kg": 0,
            "yield_per_hectare": 0,
            "revenue": 0,
            "operating_cost": 0,
            "cost_per_hectare": 0,
            "net_income": 0,
            "emissions": round(emissions, 1),
            "removals": round(removals, 1),
            "emissions_intensity": round(emissions_intensity, 3),
            "carbon_balance": round(carbon_balance, 1),
            "risk_score": risk_score,
            "esg_score": esg_score,
            "harvest_signal": _harvest_trend_signal(sheet3),
            "verification_state": verification_state,
            "certification": certification,
            "traceability_state": traceability_state,
            "invested_amount": 0,
            "expected_return": 0,
            "has_agroforestry": getattr(sheet2, "practices_agroforestry", "no") == "yes",
            "has_shade": getattr(sheet2, "has_shade_trees", "none") in ["few", "many"],
            "burns_waste": getattr(sheet2, "burns_farm_waste", "never"),
            "detail_anchor": f"farmer-{owner.id}",
            "is_high_risk": risk_score >= 65,
            "is_non_compliant": verification_state != "Verified" or risk_score >= 65,
            "time_year": timezone.now().year,
            "input_usage": "fertilizer" if getattr(sheet2, "uses_fertilizer", "no") == "yes" else "no_fertilizer",
            "yield_category": "low",
            "latitude": float(sheet1.latitude) if sheet1 and sheet1.latitude is not None else None,
            "longitude": float(sheet1.longitude) if sheet1 and sheet1.longitude is not None else None,
            "year_planted": getattr(sheet2, "year_planted", None),
        }
        farm_rows.append(row)

    farm_rows.sort(key=lambda item: (-item["net_income"], item["risk_score"]))

    total_hectares = sum(item["hectares"] for item in farm_rows)
    total_yield = sum(item["yield_kg"] for item in farm_rows)
    total_cost = sum(item["operating_cost"] for item in farm_rows)
    total_income = sum(item["net_income"] for item in farm_rows)
    total_emissions = sum(item["emissions"] for item in farm_rows)
    total_removals = sum(item["removals"] for item in farm_rows)
    total_invested = sum(item["invested_amount"] for item in farm_rows)

    overview = {
        "portfolio_scope": scope_label,
        "farm_count": len(farm_rows),
        "farmer_count": len({item["farmer_name"] for item in farm_rows}),
        "regions": len({item["region"] for item in farm_rows}),
        "capital_deployed": round(total_invested, 2),
        "yield_per_hectare": round(_safe_divide(total_yield, total_hectares), 1),
        "cost_per_hectare": round(_safe_divide(total_cost, total_hectares), 2),
        "net_income_per_farmer": round(_safe_divide(total_income, len(farm_rows)), 2),
        "emissions_intensity": round(_safe_divide(total_emissions, total_yield), 3),
        "carbon_balance": round(total_emissions - total_removals, 1),
        "deforestation_risk": round(_safe_divide(sum(item["risk_score"] for item in farm_rows), len(farm_rows)), 1),
        "esg_compliance": round(_safe_divide(sum(item["esg_score"] for item in farm_rows), len(farm_rows)), 1),
        "roi_percent": round(_safe_divide(total_income, total_invested) * 100, 1) if total_invested else 0,
        "verified_farms": sum(1 for item in farm_rows if item["verification_state"] == "Verified"),
        "high_risk_farms": sum(1 for item in farm_rows if item["is_high_risk"]),
    }

    region_cards = []
    max_region_yield = max((values["yield_kg"] for values in region_rollup.values()), default=1)
    for region, values in sorted(region_rollup.items(), key=lambda item: item[1]["yield_kg"], reverse=True):
        region_cards.append({
            "name": region,
            "farms": values["farms"],
            "yield_kg": round(values["yield_kg"], 0),
            "yield_bar": round(_safe_divide(values["yield_kg"], max_region_yield) * 100),
            "avg_esg": round(_safe_divide(values["esg_total"], values["farms"]), 1),
            "carbon_balance": round(values["carbon_balance"], 1),
            "risk_farms": values["risk_farms"],
        })

    trend_rows = []
    max_trend_yield = max((values["yield_kg"] for values in trend_rollup.values()), default=1)
    max_trend_emissions = max((values["emissions"] for values in trend_rollup.values()), default=1)
    for year in sorted(trend_rollup.keys()):
        trend_rows.append({
            "year": year,
            "yield_kg": round(trend_rollup[year]["yield_kg"], 0),
            "emissions": round(trend_rollup[year]["emissions"], 1),
            "yield_bar": round(_safe_divide(trend_rollup[year]["yield_kg"], max_trend_yield) * 100),
            "emissions_bar": round(_safe_divide(trend_rollup[year]["emissions"], max_trend_emissions) * 100),
        })

    top_opportunities = sorted(
        farm_rows,
        key=lambda item: (item["esg_score"], item["yield_per_hectare"], -item["risk_score"]),
        reverse=True,
    )[:4]
    top_risks = sorted(farm_rows, key=lambda item: (item["risk_score"], -item["esg_score"]), reverse=True)[:4]

    metric_cards = [
        {
            "label": "ROI",
            "value": f"{overview['roi_percent']}%",
            "detail": "Net income / capital deployed",
            "status": _metric_status(overview["roi_percent"], 18, 10),
        },
        {
            "label": "Yield / ha",
            "value": f"{overview['yield_per_hectare']} kg",
            "detail": "Portfolio productivity benchmark",
            "status": _metric_status(overview["yield_per_hectare"], 550, 350),
        },
        {
            "label": "Carbon balance",
            "value": f"{overview['carbon_balance']} kg CO2e",
            "detail": "Emissions minus removals",
            "status": _metric_status(overview["carbon_balance"], 0, 250, inverse=True),
        },
        {
            "label": "ESG compliance",
            "value": f"{overview['esg_compliance']} / 100",
            "detail": "Traceability + practice score",
            "status": _metric_status(overview["esg_compliance"], 75, 55),
        },
    ]

    return {
        "overview": overview,
        "metric_cards": metric_cards,
        "farm_rows": farm_rows,
        "region_cards": region_cards,
        "trend_rows": trend_rows,
        "top_opportunities": top_opportunities,
        "top_risks": top_risks,
        "region_options": all_regions,
        "selected_region": selected_region,
        "selected_size": selected_size,
        "selected_certification": selected_certification,
        "size_options": [
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        "certification_options": [
            ("certified", "Certified"),
            ("pending", "Pending Review"),
        ],
        "investor_profile": UserProfile.objects.filter(user=user).first(),
    }
# -------------------------------
# Farmer ViewSet
# -------------------------------
class FarmerViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Farmer.objects.all()
        elif user.role == 'field_agent':
            return Farmer.objects.filter(created_by=user)
        return Farmer.objects.filter(id=user.id)  # Farmer sees only self

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create a farmer.")


# -------------------------------
# Farm ViewSet
# -------------------------------
class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Farm.objects.all()
        elif user.role == 'field_agent':
            return Farm.objects.filter(farmer__created_by=user)
        elif user.role == 'farmer':
            return Farm.objects.filter(farmer=user)
        return Farm.objects.none()  # Investors cannot modify farms

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create a farm.")


# -------------------------------
# Harvest ViewSet
# -------------------------------
class HarvestViewSet(viewsets.ModelViewSet):
    serializer_class = HarvestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Harvest.objects.all()
        elif user.role == 'field_agent':
            return Harvest.objects.filter(farm__farmer__created_by=user)
        elif user.role == 'farmer':
            return Harvest.objects.filter(farm__farmer=user)
        elif user.role == 'investor':
            return Harvest.objects.all()
        return Harvest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent', 'farmer']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create a harvest.")


# -------------------------------
# Investment ViewSet
# -------------------------------
class InvestmentViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Investment.objects.all()
        elif user.role == 'investor':
            return Investment.objects.filter(farmer=user)
        elif user.role == 'farmer':
            return Investment.objects.filter(farmer=user)
        return Investment.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'investor']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create an investment.")


# -------------------------------
# FarmActivity ViewSet
# -------------------------------
class FarmActivityViewSet(viewsets.ModelViewSet):
    serializer_class = FarmActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return FarmActivity.objects.all()
        elif user.role == 'field_agent':
            return FarmActivity.objects.filter(farmer__created_by=user)
        elif user.role == 'farmer':
            return FarmActivity.objects.filter(farmer=user)
        elif user.role == 'investor':
            return FarmActivity.objects.all()
        return FarmActivity.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent', 'farmer']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create farm activity.")


# -------------------------------
# Farmer Registration (public)
# -------------------------------
class FarmerRegistrationView(generics.CreateAPIView):
    serializer_class = FarmerRegistrationSerializer
    permission_classes = []  # Public endpoint

# -------------------------------
# Announcements ViewSet (read-only)
# -------------------------------
class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns a list of active announcements
    """
    queryset = Announcement.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = AnnouncementSerializer


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Message.objects.all()

        if user.role in ['field_agent', 'farmer']:
            return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)

        return Message.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        receiver = serializer.validated_data['receiver']

        if user.role == 'farmer' and receiver.is_superuser:
            raise PermissionDenied("Farmers cannot message admin.")

        if user.role == 'farmer' and receiver.role != 'field_agent':
            raise PermissionDenied("Farmers can only message field agents.")

        serializer.save(sender=user)


# =================================================
# Messaging HTML Views
# =================================================

def _get_role(user):
    """Return the profile role string, or 'admin' for superuser."""
    if user.is_superuser:
        return "admin"
    try:
        return user.profile.role
    except Exception:
        return None


def _get_announcements_for_user(user, role):
    """Return Announcement queryset visible to this user based on their role."""
    qs = Announcement.objects.filter(is_active=True)
    if role == "farmer":
        agent = getattr(getattr(user, "profile", None), "created_by_agent", None)
        return qs.filter(
            Q(target_audience="all_farmers")
            | Q(target_audience="all")
            | Q(target_audience="agent_farmers", target_agent=agent)
        ).order_by("-created_at")
    elif role == "field_agent":
        return qs.filter(
            Q(target_audience="all_field_agents") | Q(target_audience="all")
        ).order_by("-created_at")
    elif role in ("investor", "analyst"):
        return qs.none()
    elif role == "admin":
        return qs.order_by("-created_at")
    # If role is None or unknown, show nothing
    return qs.none()


def _can_message(sender, sender_role, receiver):
    """Return True if sender is permitted to send a direct message to receiver."""
    if not sender_role or sender_role is None:
        return False
    if sender.id == receiver.id:
        return False
    receiver_role = _get_role(receiver)
    if not receiver_role or receiver_role is None:
        return False
    receiver_is_admin = receiver_role == "admin"

    if sender_role == "farmer":
        agent = getattr(getattr(sender, "profile", None), "created_by_agent", None)
        return agent is not None and agent.id == receiver.id

    if sender_role == "field_agent":
        if receiver_is_admin:
            return True
        if receiver_role == "farmer":
            return UserProfile.objects.filter(
                user=receiver, created_by_agent=sender
            ).exists()
        return False

    if sender_role in ("investor", "analyst"):
        return receiver_is_admin

    if sender_role == "admin":
        return receiver_role in ("farmer", "field_agent", "admin")

    return False


def _get_compose_targets(user, role):
    """Return queryset of users the current user is allowed to compose to."""
    if not role:
        return Farmer.objects.none()
    
    if role == "farmer":
        agent = getattr(getattr(user, "profile", None), "created_by_agent", None)
        if agent:
            return Farmer.objects.filter(pk=agent.pk)
        return Farmer.objects.none()

    if role == "field_agent":
        farmer_ids = UserProfile.objects.filter(
            created_by_agent=user, role="farmer"
        ).values_list("user_id", flat=True)
        admin_ids = UserProfile.objects.filter(role="admin").values_list("user_id", flat=True)
        superuser_ids = Farmer.objects.filter(is_superuser=True).values_list("id", flat=True)
        return (
            Farmer.objects.filter(
                Q(id__in=farmer_ids) | Q(id__in=admin_ids) | Q(id__in=superuser_ids)
            ).exclude(pk=user.pk)
        )

    if role in ("investor", "analyst"):
        admin_ids = UserProfile.objects.filter(role="admin").values_list("user_id", flat=True)
        superuser_ids = Farmer.objects.filter(is_superuser=True).values_list("id", flat=True)
        return Farmer.objects.filter(
            Q(id__in=admin_ids) | Q(id__in=superuser_ids)
        ).exclude(pk=user.pk)

    if role == "admin":
        target_ids = UserProfile.objects.filter(
            role__in=("farmer", "field_agent", "admin")
        ).values_list("user_id", flat=True)
        superuser_ids = Farmer.objects.filter(is_superuser=True).values_list("id", flat=True)
        return Farmer.objects.filter(
            Q(id__in=target_ids) | Q(id__in=superuser_ids)
        ).exclude(pk=user.pk)

    return Farmer.objects.none()


@login_required
def inbox(request):
    user = request.user
    role = _get_role(user)

    # Ensure user has a profile
    if role is None:
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": "farmer"})
        role = profile.role

    # Prevent anonymous/unrecognized users from accessing
    if role is None:
        return HttpResponseForbidden("User role not recognized.")

    # ---- conversation sidebar ----
    sent_ids = Message.objects.filter(sender=user).values_list("receiver_id", flat=True).distinct()
    recv_ids = Message.objects.filter(receiver=user).values_list("sender_id", flat=True).distinct()
    convo_ids = set(list(sent_ids) + list(recv_ids))

    conversations = []
    for uid in convo_ids:
        try:
            other = Farmer.objects.get(pk=uid)
            last_msg = (
                Message.objects.filter(
                    Q(sender=user, receiver=other) | Q(sender=other, receiver=user)
                )
                .order_by("-created_at")
                .first()
            )
            unread = Message.objects.filter(sender=other, receiver=user, is_read=False).count()
            conversations.append({"user": other, "last_message": last_msg, "unread": unread})
        except Farmer.DoesNotExist:
            pass

    conversations.sort(
        key=lambda x: x["last_message"].created_at if x["last_message"] else datetime.min,
        reverse=True,
    )

    # ---- selected conversation or announcement ----
    selected_user = None
    thread = []
    selected_announcement = None

    with_id = request.GET.get("with")
    ann_id = request.GET.get("ann")

    if with_id:
        try:
            candidate = Farmer.objects.get(pk=with_id)
            if _can_message(user, role, candidate):
                selected_user = candidate
                # mark incoming as read
                Message.objects.filter(
                    sender=selected_user, receiver=user, is_read=False
                ).update(is_read=True)
                thread = list(
                    Message.objects.filter(
                        Q(sender=user, receiver=selected_user)
                        | Q(sender=selected_user, receiver=user)
                    ).order_by("created_at")
                )
        except Farmer.DoesNotExist:
            pass

    elif ann_id:
        try:
            ann_qs = _get_announcements_for_user(user, role)
            selected_announcement = ann_qs.get(pk=ann_id)
        except Announcement.DoesNotExist:
            pass

    # ---- handle POST (send message) ----
    if request.method == "POST" and selected_user and role:
        content = request.POST.get("content", "").strip()
        if content:
            try:
                if _can_message(user, role, selected_user):
                    Message.objects.create(sender=user, receiver=selected_user, content=content)
            except Exception as e:
                import sys
                print(f"Error sending message: {e}", file=sys.stderr)
        return redirect(f"{reverse('inbox')}?with={selected_user.pk}")

    announcements = _get_announcements_for_user(user, role)
    compose_targets = list(_get_compose_targets(user, role).values("id", "username", "first_name", "last_name"))
    can_broadcast = role in ("field_agent", "admin")

    total_unread = Message.objects.filter(receiver=user, is_read=False).count()
    notifications = Notification.objects.filter(recipient=user).order_by('-created_at')[:50]
    total_unread_notifications = Notification.objects.filter(recipient=user, is_read=False).count()

    return render(request, "Farmers/inbox.html", {
        "conversations": conversations,
        "selected_user": selected_user,
        "thread": thread,
        "selected_announcement": selected_announcement,
        "announcements": announcements,
        "compose_targets": compose_targets,
        "can_broadcast": can_broadcast,
        "role": role,
        "total_unread": total_unread,
        "notifications": notifications,
        "total_unread_notifications": total_unread_notifications,
    })


@login_required
def broadcast(request):
    user = request.user
    role = _get_role(user)

    if role not in ("field_agent", "admin"):
        return redirect("inbox")

    error = None
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        body = request.POST.get("message", "").strip()
        if not title or not body:
            error = "Title and message are required."
        else:
            if role == "field_agent":
                Announcement.objects.create(
                    title=title,
                    message=body,
                    created_by=user,
                    target_audience="agent_farmers",
                    target_agent=user,
                )
            else:
                audience = request.POST.get("target_audience", "all")
                if audience not in ("all_farmers", "all_field_agents", "all"):
                    audience = "all"
                Announcement.objects.create(
                    title=title,
                    message=body,
                    created_by=user,
                    target_audience=audience,
                )
            return redirect("inbox")

    return render(request, "Farmers/broadcast.html", {"role": role, "error": error})


@login_required
def mark_message_read(request, message_id):
    if request.method == "POST":
        Message.objects.filter(pk=message_id, receiver=request.user).update(is_read=True)
    return JsonResponse({"ok": True})


@login_required
def mark_notification_read(request, notification_id):
    if request.method == "POST":
        Notification.objects.filter(pk=notification_id, recipient=request.user).update(is_read=True)
    return JsonResponse({"ok": True})


@approved_user_required
def dashboard(request):
    return render(request, "Farmers/dashboard.html")


def service_worker(request):
    """Serve the PWA service worker at /sw.js (root scope required)."""
    content = render(request, "Farmers/sw.js").content
    return HttpResponse(content, content_type="application/javascript")


def home(request):
    is_ajax_request = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":
        form = HomeContactForm(request.POST)
        if form.is_valid():
            admin_users = Farmer.objects.filter(profile__role="admin", is_active=True)
            if not admin_users.exists():
                if is_ajax_request:
                    return JsonResponse(
                        {
                            "ok": False,
                            "message": "No active admin is available to receive your request right now.",
                        },
                        status=503,
                    )
                messages.error(request, "No active admin is available to receive your request right now.")
            else:
                payload = form.cleaned_data
                ContactSubmission.objects.create(
                    name=payload["name"],
                    email=payload["email"],
                    phone=payload["phone"],
                    nationel=payload["nationel"],
                    current_resident=payload["current_resident"],
                    reason_for_contact=payload["reason_for_contact"],
                )

                notification_message = (
                    "New homepage Contact Us request received.\n"
                    f"Name: {payload['name']}\n"
                    f"Email: {payload['email']}\n"
                    f"Phone: {payload['phone']}\n"
                    f"Nationel: {payload['nationel']}\n"
                    f"Current Resident: {payload['current_resident']}\n"
                    f"Reason: {payload['reason_for_contact']}"
                )
                AdminNotification.objects.bulk_create([
                    AdminNotification(
                        recipient=admin_user,
                        notification_type="info",
                        message=notification_message,
                    )
                    for admin_user in admin_users
                ])

                admin_emails = list(
                    admin_users.exclude(email="").exclude(email__isnull=True).values_list("email", flat=True)
                )
                if admin_emails:
                    send_mail(
                        subject="New Contact Us Submission - 1847 Ventures",
                        message=notification_message,
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        recipient_list=admin_emails,
                        fail_silently=True,
                    )

                if is_ajax_request:
                    return JsonResponse(
                        {
                            "ok": True,
                            "message": "Thank you. Your request has been submitted to the admin team.",
                        }
                    )

                messages.success(request, "Thank you. Your request has been submitted to the admin team.")
                return redirect("home")
        elif is_ajax_request:
            errors = {
                field: [str(error) for error in field_errors]
                for field, field_errors in form.errors.items()
            }
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Please correct the highlighted fields and try again.",
                    "errors": errors,
                },
                status=400,
            )
    else:
        form = HomeContactForm()

    return render(request, "Farmers/home.html", {"contact_form": form})


def app_download(request):
    target = (request.GET.get("target") or "desktop").strip().lower()
    if target not in {"desktop", "android"}:
        target = "desktop"
    return render(request, "Farmers/app_download.html", {"target": target})

class CustomLoginView(LoginView):
    template_name = "Farmers/login.html"

    def form_valid(self, form):
        user = form.get_user()

        # Ensure profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)

        # Block unapproved users (except superuser)
        if not user.is_superuser and not profile.is_approved:
            messages.error(self.request, "Your account is not yet approved.")
            return redirect('login')

        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user

        # Ensure profile exists again safely
        profile, created = UserProfile.objects.get_or_create(user=user)

        if user.is_superuser:
            return reverse_lazy('superuser_dashboard_selector')

        if profile.must_change_password:
            return reverse_lazy('force_password_change')

        role = profile.role

        if role == 'admin':
            return reverse_lazy('admin_dashboard')

        if role == 'farmer':
            return reverse_lazy('farmer_dashboard')

        if role == 'field_agent':
            return reverse_lazy('agent_dashboard')

        if role == 'investor':
            return reverse_lazy('partner_dashboard')

        if role == 'analyst':
            return reverse_lazy('partner_dashboard')

        return reverse_lazy('home')


def _dashboard_url_for_user(user):
    if user.is_superuser:
        return reverse('superuser_dashboard_selector')

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.role == 'admin':
        return reverse('admin_dashboard')
    if profile.role == 'farmer':
        return reverse('farmer_dashboard')
    if profile.role == 'field_agent':
        return reverse('agent_dashboard')
    if profile.role == 'investor':
        return reverse('partner_dashboard')
    if profile.role == 'analyst':
        return reverse('partner_dashboard')
    return reverse('home')


@login_required
def force_password_change(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.must_change_password:
        return redirect(_dashboard_url_for_user(request.user))

    if request.method == "POST":
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password"])
            messages.success(request, "Password updated successfully. You now have full access.")
            return redirect(_dashboard_url_for_user(request.user))
    else:
        form = SetPasswordForm(request.user)

    return render(request, "Farmers/force_password_change.html", {"form": form})


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('home')


def _superuser_dashboard_links():
    return [
        {"label": "Admin Dashboard", "url": reverse("admin_dashboard"), "description": "Operational admin dashboard for users and approvals."},
        {"label": "Django Admin", "url": reverse("admin:index"), "description": "Full Django admin site controls."},
        {"label": "Partner Dashboard", "url": reverse("partner_dashboard"), "description": "Investor and analyst analytics dashboard."},
        {"label": "External Data Analysis", "url": reverse("partner_external_analysis"), "description": "Partner external dataset analysis workspace."},
        {"label": "External Dataset Intelligence", "url": reverse("partner_external_dataset_intelligence"), "description": "Isolated external dataset intelligence workspace."},
        {"label": "Standalone Data Analysis", "url": reverse("partner_standalone_analysis"), "description": "Partner standalone dataset analysis workspace."},
        {"label": "Field Agent Dashboard", "url": reverse("agent_dashboard"), "description": "Agent operations and farmer assignment view."},
        {"label": "Farmer Dashboard", "url": reverse("farmer_dashboard"), "description": "Farmer-facing dashboard experience."},
    ]


def _is_allowed_superuser_target(target_url):
    parsed_target = parse.urlsplit(target_url or "")
    if parsed_target.scheme or parsed_target.netloc:
        return False

    target_path = parsed_target.path
    if not target_path:
        return False

    allowed_paths = {parse.urlsplit(item["url"]).path for item in _superuser_dashboard_links()}
    if target_path in allowed_paths:
        return True

    # Auto-allow approved in-app scopes so dashboard subpages are always reachable after selection.
    if _superuser_gate_scope_for_path(target_path):
        try:
            resolve(target_path)
            return True
        except Resolver404:
            return False

    # Auto-allow approved partner routes so newly added partner pages do not require manual link updates.
    try:
        match = resolve(target_path)
    except Resolver404:
        return False

    url_name = (match.url_name or "").strip()
    is_approved_partner_name = any(url_name.startswith(prefix) for prefix in APPROVED_SUPERUSER_PARTNER_ROUTE_PREFIXES)
    is_approved_partner_path = any(target_path.startswith(prefix) for prefix in APPROVED_SUPERUSER_PARTNER_PATH_PREFIXES)
    return is_approved_partner_name and is_approved_partner_path


def _superuser_gate_scope_for_path(path):
    normalized_path = (path or "").strip()
    for scope, prefixes in SUPERUSER_SCOPE_PREFIXES.items():
        if any(normalized_path.startswith(prefix) for prefix in prefixes):
            return scope
    return ""


def _is_path_allowed_for_superuser_scope(path, scope):
    prefixes = SUPERUSER_SCOPE_PREFIXES.get(scope, ())
    if not prefixes:
        return False
    return any((path or "").startswith(prefix) for prefix in prefixes)


def _enforce_superuser_dashboard_gate(request):
    if not request.user.is_superuser:
        return None

    current_path = request.path
    allowed_scope = request.session.get("superuser_gate_allowed_scope", "")
    if _is_path_allowed_for_superuser_scope(current_path, allowed_scope):
        return None

    allowed_path = request.session.get("superuser_gate_allowed_path", "")
    if allowed_path == current_path:
        return None

    next_url = request.get_full_path()
    gate_url = f"{reverse('superuser_dashboard_gate')}?{parse.urlencode({'next': next_url})}"
    return redirect(gate_url)


@login_required
def superuser_dashboard_selector(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied")

    dashboard_links = _superuser_dashboard_links()

    return render(
        request,
        "Farmers/superuser_dashboard_selector.html",
        {"dashboard_links": dashboard_links},
    )


@login_required
def superuser_dashboard_gate(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied")

    target = (request.POST.get("next") if request.method == "POST" else request.GET.get("next")) or ""
    if not target:
        return redirect("superuser_dashboard_selector")

    if not _is_allowed_superuser_target(target):
        return HttpResponseForbidden("Invalid dashboard target")

    target_path = parse.urlsplit(target).path
    target_scope = _superuser_gate_scope_for_path(target_path)
    selected = next((item for item in _superuser_dashboard_links() if parse.urlsplit(item["url"]).path == target_path), None)
    target_label = selected["label"] if selected else "Selected dashboard"

    if request.method == "POST":
        password = request.POST.get("password", "")
        if request.user.check_password(password):
            request.session["superuser_gate_allowed_path"] = target_path
            request.session["superuser_gate_allowed_scope"] = target_scope
            return redirect(target)
        messages.error(request, "Incorrect password. Please try again.")

    return render(
        request,
        "Farmers/superuser_dashboard_gate.html",
        {
            "target": target,
            "target_label": target_label,
        },
    )

@login_required
def farmer_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not request.user.is_superuser and profile.role != "farmer":
        return redirect(_dashboard_url_for_user(request.user))
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied
    unread_notifications_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    activity_form = FarmerActivitySubmissionForm()
    recent_activities = request.user.activities.select_related("verified_by", "admin_reviewed_by").order_by("-created_at")[:12]
    activity_stats = {
        "total": request.user.activities.count(),
        "pending_verification": request.user.activities.filter(verification_status="pending").count(),
        "verified_waiting_admin": request.user.activities.filter(verification_status="verified", admin_approval_status="pending").count(),
        "approved": request.user.activities.filter(admin_approval_status="approved").count(),
    }

    sheet2 = getattr(request.user, "assessment_sheet2", None)
    farmer_profile = {
        "full_name": getattr(getattr(request.user, "assessment_sheet1", None), "full_name", ""),
        "location": getattr(getattr(request.user, "assessment_sheet1", None), "location_name", ""),
        "farm_size": sheet2.get_farm_size_category_display() if sheet2 else "",
        "has_shade_trees": sheet2.get_has_shade_trees_display() if sheet2 else "",
    }
    sheet3 = getattr(request.user, "assessment_sheet3", None)
    farmer_profile_photo_url = ""
    if getattr(profile, "profile_photo", None):
        farmer_profile_photo_url = profile.profile_photo.url
    elif sheet3 and getattr(sheet3, "photo_of_farmer", None):
        farmer_profile_photo_url = sheet3.photo_of_farmer.url

    return render(
        request,
        "Farmers/farmer_dashboard.html",
        {
            "unread_notifications_count": unread_notifications_count,
            "activity_form": activity_form,
            "recent_activities": recent_activities,
            "activity_stats": activity_stats,
            "farmer_profile": farmer_profile,
            "farmer_profile_photo_url": farmer_profile_photo_url,
        },
    )


@login_required
def submit_farmer_activity(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not request.user.is_superuser and profile.role != "farmer":
        return HttpResponseForbidden("Access Denied")

    if request.method != "POST":
        return redirect("farmer_dashboard")

    activity_form = FarmerActivitySubmissionForm(request.POST)
    if not activity_form.is_valid():
        messages.error(request, "Please fix the highlighted activity fields and submit again.")
        unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        sheet3 = getattr(request.user, "assessment_sheet3", None)
        farmer_profile_photo_url = ""
        if getattr(profile, "profile_photo", None):
            farmer_profile_photo_url = profile.profile_photo.url
        elif sheet3 and getattr(sheet3, "photo_of_farmer", None):
            farmer_profile_photo_url = sheet3.photo_of_farmer.url
        return render(
            request,
            "Farmers/farmer_dashboard.html",
            {
                "unread_notifications_count": unread_notifications_count,
                "activity_form": activity_form,
                "recent_activities": request.user.activities.order_by("-created_at")[:12],
                "activity_stats": {
                    "total": request.user.activities.count(),
                    "pending_verification": request.user.activities.filter(verification_status="pending").count(),
                    "verified_waiting_admin": request.user.activities.filter(verification_status="verified", admin_approval_status="pending").count(),
                    "approved": request.user.activities.filter(admin_approval_status="approved").count(),
                },
                "farmer_profile": {
                    "full_name": getattr(getattr(request.user, "assessment_sheet1", None), "full_name", ""),
                    "location": getattr(getattr(request.user, "assessment_sheet1", None), "location_name", ""),
                    "farm_size": getattr(getattr(request.user, "assessment_sheet2", None), "get_farm_size_category_display", lambda: "")(),
                    "has_shade_trees": getattr(getattr(request.user, "assessment_sheet2", None), "get_has_shade_trees_display", lambda: "")(),
                },
                "farmer_profile_photo_url": farmer_profile_photo_url,
            },
        )

    created_by_agent = getattr(profile, "created_by_agent", None)
    if not created_by_agent:
        messages.error(request, "No field agent is linked to your account yet. Contact support before submitting activities.")
        return redirect("farmer_dashboard")

    activity = activity_form.save(commit=False)
    activity.farmer = request.user
    activity.verification_status = "pending"
    activity.admin_approval_status = "pending"
    activity.save()

    Message.objects.create(
        sender=request.user,
        receiver=created_by_agent,
        content=(
            f"Farmer activity submitted by '{request.user.username}'. "
            f"Please verify: {activity.get_activity_type_display()} on {activity.date}."
        ),
    )

    messages.success(request, "Activity submitted. Your field agent must verify it before admin review.")
    return redirect("farmer_dashboard")


@login_required
def agent_dashboard(request):
    if not _user_has_role(request.user, {"field_agent"}):
        return HttpResponseForbidden("Access Denied")
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied
    agent_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    farmers = _field_agent_farmer_queryset(request.user).order_by('-registration_date')
    pending_requests = FarmerRegistrationRequest.objects.filter(
        assigned_agent=request.user, status='pending'
    )
    
    # Get agent stats
    total_farmers = farmers.count()
    approved_farmers = farmers.filter(profile__is_approved=True).count()
    pending_approval = farmers.filter(profile__is_approved=False).count()
    pending_assignments = pending_requests.count()
    
    unread_notifications_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    pending_activity_verifications = FarmActivity.objects.filter(
        farmer__profile__created_by_agent=request.user,
        verification_status="pending",
    ).select_related("farmer").order_by("-created_at")
    return render(request, "Farmers/agent_dashboard.html", {
        "agent_profile": agent_profile,
        "farmers": farmers,
        "pending_requests": pending_requests,
        "pending_activity_verifications": pending_activity_verifications,
        "total_farmers": total_farmers,
        "approved_farmers": approved_farmers,
        "pending_approval": pending_approval,
        "pending_assignments": pending_assignments,
        "unread_messages_count": Message.objects.filter(receiver=request.user, is_read=False).count(),
        "unread_notifications_count": unread_notifications_count,
    })


@login_required
def verify_farmer_activity(request, activity_id):
    if not _user_has_role(request.user, {"field_agent"}):
        return HttpResponseForbidden("Access Denied")

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    activity = get_object_or_404(
        FarmActivity,
        pk=activity_id,
        farmer__profile__created_by_agent=request.user,
    )

    activity.verification_status = "verified"
    activity.verified_by = request.user
    activity.verified_at = timezone.now()
    activity.agent_verification_notes = request.POST.get("agent_note", "").strip()
    activity.admin_approval_status = "pending"
    activity.save(update_fields=[
        "verification_status",
        "verified_by",
        "verified_at",
        "agent_verification_notes",
        "admin_approval_status",
        "updated_at",
    ])

    admin_users = Farmer.objects.filter(profile__role="admin", is_active=True)
    AdminNotification.objects.bulk_create([
        AdminNotification(
            recipient=admin_user,
            notification_type="info",
            message=(
                f"Field agent {request.user.username} verified activity for farmer "
                f"{activity.farmer.username}: {activity.get_activity_type_display()}."
            ),
            related_farmer=activity.farmer,
        )
        for admin_user in admin_users
    ])

    messages.success(request, f"Activity for {activity.farmer.username} verified and sent to admin for approval.")
    return redirect("agent_dashboard")


@login_required
def reject_farmer_activity_verification(request, activity_id):
    if not _user_has_role(request.user, {"field_agent"}):
        return HttpResponseForbidden("Access Denied")

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    activity = get_object_or_404(
        FarmActivity,
        pk=activity_id,
        farmer__profile__created_by_agent=request.user,
    )

    rejection_note = request.POST.get("agent_note", "").strip() or "Needs correction before verification."
    activity.verification_status = "rejected"
    activity.verified_by = request.user
    activity.verified_at = timezone.now()
    activity.agent_verification_notes = rejection_note
    activity.admin_approval_status = "rejected"
    activity.save(update_fields=[
        "verification_status",
        "verified_by",
        "verified_at",
        "agent_verification_notes",
        "admin_approval_status",
        "updated_at",
    ])

    Message.objects.create(
        sender=request.user,
        receiver=activity.farmer,
        content=(
            f"Your activity update ({activity.get_activity_type_display()} on {activity.date}) "
            f"needs correction before admin review. Note: {rejection_note}"
        ),
    )

    messages.warning(request, f"Activity for {activity.farmer.username} was returned for correction.")
    return redirect("agent_dashboard")


def _prepare_profile_photo(photo, post_data):
    """Create a square avatar image using client preview adjustments."""
    try:
        zoom = float(post_data.get("profile_zoom", "1"))
    except (TypeError, ValueError):
        zoom = 1.0
    try:
        shift_x = float(post_data.get("profile_shift_x", "0"))
    except (TypeError, ValueError):
        shift_x = 0.0
    try:
        shift_y = float(post_data.get("profile_shift_y", "0"))
    except (TypeError, ValueError):
        shift_y = 0.0

    zoom = max(1.0, min(3.0, zoom))
    shift_x = max(-100.0, min(100.0, shift_x))
    shift_y = max(-100.0, min(100.0, shift_y))

    image = Image.open(photo)
    image = ImageOps.exif_transpose(image)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    width, height = image.size
    min_side = min(width, height)
    crop_size = max(int(min_side / zoom), 1)

    max_dx = (width - crop_size) / 2
    max_dy = (height - crop_size) / 2
    center_x = (width / 2) + (shift_x / 100.0) * max_dx
    center_y = (height / 2) + (shift_y / 100.0) * max_dy

    left = int(round(center_x - (crop_size / 2)))
    top = int(round(center_y - (crop_size / 2)))
    left = max(0, min(left, width - crop_size))
    top = max(0, min(top, height - crop_size))

    cropped = image.crop((left, top, left + crop_size, top + crop_size)).resize((512, 512), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=92, optimize=True)
    buffer.seek(0)

    stem, _ = os.path.splitext(photo.name or "profile")
    filename = f"{stem}_profile_{uuid.uuid4().hex[:8]}.jpg"
    return ContentFile(buffer.getvalue(), name=filename)


@login_required
def upload_agent_profile_photo(request):
    """Allow field agents to upload their profile photo"""
    if not _user_has_role(request.user, {"field_agent"}):
        return HttpResponseForbidden("Access Denied")

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    photo = request.FILES.get("profile_photo")
    if not photo:
        messages.error(request, "Please choose an image file first.")
        return redirect("agent_dashboard")

    agent_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    agent_profile.profile_photo = _prepare_profile_photo(photo, request.POST)
    agent_profile.save(update_fields=["profile_photo"])
    messages.success(request, "✓ Profile picture updated successfully.")
    return redirect("agent_dashboard")


@login_required
def create_farmer(request):
    if not _user_has_role(request.user, {"field_agent"}):
        return HttpResponseForbidden("Access Denied")

    if request.method == "POST":
        form = FarmerCreateByAgentForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            gps_captured = bool(form.cleaned_data["latitude"] and form.cleaned_data["longitude"])
            photos_complete = bool(form.cleaned_data["photo_of_farmer"] and form.cleaned_data["photo_of_farm"])

            with transaction.atomic():
                farmer = Farmer(username=username, email=email)
                farmer.set_unusable_password()
                farmer.save()

                profile = farmer.profile
                profile.role = "farmer"
                profile.is_approved = False
                profile.created_by_agent = request.user
                profile.profile_photo = form.cleaned_data["photo_of_farmer"]
                profile.save()

                FarmAssessmentSheet1.objects.update_or_create(
                    farmer=farmer,
                    defaults={
                        "full_name": form.cleaned_data["full_name"],
                        "household_size": form.cleaned_data["household_size"],
                        "belongs_to_group": form.cleaned_data["belongs_to_group"],
                        "farmer_group_name": form.cleaned_data.get("farmer_group_name", ""),
                        "latitude": form.cleaned_data["latitude"],
                        "longitude": form.cleaned_data["longitude"],
                        "location_name": form.cleaned_data.get("location_name", ""),
                        "gps_captured": gps_captured,
                        "land_ownership": form.cleaned_data["land_ownership"],
                        "collected_by": request.user,
                    },
                )

                FarmAssessmentSheet2.objects.update_or_create(
                    farmer=farmer,
                    defaults={
                        "year_planted": form.cleaned_data.get("year_planted") or None,
                        "farm_size_category": form.cleaned_data["farm_size_category"],
                        "has_shade_trees": form.cleaned_data["has_shade_trees"],
                        "shade_tree_types": form.cleaned_data.get("shade_tree_types", ""),
                        "uses_fertilizer": form.cleaned_data["uses_fertilizer"],
                        "fertilizer_bag_range": form.cleaned_data.get("fertilizer_bag_range", "none"),
                        "fertilizer_application": form.cleaned_data.get("fertilizer_application", ""),
                        "burns_farm_waste": form.cleaned_data["burns_farm_waste"],
                        "practices_agroforestry": form.cleaned_data["practices_agroforestry"],
                        "received_training": form.cleaned_data["received_training"],
                        "plants_trees": form.cleaned_data["plants_trees"],
                        "collected_by": request.user,
                    },
                )

                anomaly_notes = []
                if form.cleaned_data["has_shade_trees"] == "none" and form.cleaned_data["practices_agroforestry"] == "yes":
                    anomaly_notes.append("Inconsistency: no shade trees selected but agroforestry marked yes.")

                FarmAssessmentSheet3.objects.update_or_create(
                    farmer=farmer,
                    defaults={
                        "harvest_history": {
                            str(datetime.today().year - 1): form.cleaned_data.get("harvest_y1_bags", ""),
                            **({str(datetime.today().year - 2): form.cleaned_data["harvest_y2_bags"]} if form.cleaned_data.get("harvest_y2_bags") else {}),
                            **({str(datetime.today().year - 3): form.cleaned_data["harvest_y3_bags"]} if form.cleaned_data.get("harvest_y3_bags") else {}),
                        },
                        "photo_of_farmer": form.cleaned_data["photo_of_farmer"],
                        "photo_of_farm": form.cleaned_data["photo_of_farm"],
                        "voice_note": form.cleaned_data.get("voice_note"),
                        "photos_complete": photos_complete,
                        "data_validated": len(anomaly_notes) == 0,
                        "validation_notes": " ".join(anomaly_notes),
                        "collected_by": request.user,
                    },
                )

                request_id = request.POST.get("request_id")
                if request_id:
                    try:
                        reg_request = FarmerRegistrationRequest.objects.get(
                            pk=request_id, assigned_agent=request.user, status='pending'
                        )
                        reg_request.status = 'completed'
                        reg_request.save()
                    except FarmerRegistrationRequest.DoesNotExist:
                        pass

                admin_users = Farmer.objects.filter(profile__role='admin', is_active=True)
                notification_message = (
                    f"Field agent '{request.user.username}' has registered a new farmer: "
                    f"'{username}' ({email}). Pending your approval."
                )
                AdminNotification.objects.bulk_create([
                    AdminNotification(
                        recipient=admin_user,
                        notification_type='new_farmer',
                        message=notification_message,
                        related_farmer=farmer,
                    )
                    for admin_user in admin_users
                ])

            messages.success(
                request,
                f"Farmer '{username}' has been registered with full intake data and is pending admin approval."
            )
            return redirect("agent_dashboard")
    else:
        form = FarmerCreateByAgentForm()

    request_id = request.GET.get("request_id", "")
    return render(request, "Farmers/create_farmer.html", {"form": form, "request_id": request_id})


@login_required
def partner_dashboard(request):
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied

    selected_region = request.GET.get("region", "")
    selected_size = request.GET.get("farm_size", "")
    selected_certification = request.GET.get("certification", "")
    cache_key = _build_cache_key(
        "partner_dashboard",
        request.user.id,
        selected_region,
        selected_size,
        selected_certification,
    )
    context = cache.get(cache_key)
    if context is None:
        context = _build_partner_dashboard_context(
            request.user,
            selected_region=selected_region,
            selected_size=selected_size,
            selected_certification=selected_certification,
        )
        cache.set(cache_key, context, DASHBOARD_CACHE_TTL_SECONDS)

    latest_dataset = (
        InvestorDatasetImport.objects.filter(investor=request.user)
        .order_by("-created_at")
        .first()
    )
    latest_dataset_ai_summary = None
    if latest_dataset and isinstance(latest_dataset.stats, dict):
        latest_dataset_ai_summary = latest_dataset.stats.get("ai_investment_insight_summary")

    context = dict(context)
    # Always fetch investor_profile fresh — bypasses the cached snapshot so
    # a just-uploaded profile photo is reflected immediately on redirect.
    context["investor_profile"] = UserProfile.objects.filter(user=request.user).first()
    requested_view = (request.GET.get("view") or "").strip()
    valid_page_ids = {item["id"] for item in ENTERPRISE_WORKSPACE_PAGES}
    context["initial_workspace_view"] = requested_view if requested_view in valid_page_ids else "investor-dashboard"
    context["enterprise_workspace_pages"] = ENTERPRISE_WORKSPACE_PAGES
    context["field_agent_form_schema"] = FIELD_AGENT_FORM_SCHEMA
    context["visualization_catalog"] = VISUALIZATION_CATALOG
    context["latest_dataset_ai_summary"] = latest_dataset_ai_summary
    context["unread_notifications_count"] = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    context["pending_farmer_deletion_requests"] = FarmerDeletionRequest.objects.filter(
        status="pending_partner_approval"
    ).select_related("farmer", "requested_by")[:40]

    return render(request, "Farmers/partner_dashboard.html", context)


def _build_dataset_analytics(schema, rows_qs, precomputed_stats=None):
    """
    Pre-compute column-type-driven analytics from an uploaded dataset.
    Returns four sections: executive_summary, distribution_data,
    trend_data, and correlation_pairs — all ready for Chart.js.
    """
    numeric_cols = [c["column"] for c in schema if c["type"] in ("integer", "float")]
    categorical_cols = [c["column"] for c in schema if c["type"] in ("string", "boolean")]
    date_cols = [c["column"] for c in schema if c["type"] == "date"]

    rows = [row.payload for row in rows_qs.order_by("row_number")[:500]]
    columnar_storage = (precomputed_stats or {}).get("columnar_storage", {}) if precomputed_stats else {}
    aggregated_columns = (precomputed_stats or {}).get("aggregated_columns", {}) if precomputed_stats else {}

    def _sample_values(column):
        column_data = (columnar_storage.get("columns") or {}).get(column, {})
        values = column_data.get("values", [])
        return values or [row.get(column) for row in rows]

    if not rows:
        return None

    # ── Executive summary ────────────────────────────────────────────
    numeric_stats = {}
    for col in numeric_cols:
        precomputed = aggregated_columns.get(col) if aggregated_columns else None
        if precomputed and precomputed.get("non_null_count"):
            numeric_stats[col] = {
                "min": precomputed.get("min"),
                "max": precomputed.get("max"),
                "mean": precomputed.get("mean"),
                "count": precomputed.get("non_null_count"),
            }
            continue

        values = []
        for row in rows:
            value = row.get(col)
            if value is None:
                continue
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                continue
        if values:
            numeric_stats[col] = {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "mean": round(statistics.mean(values), 2),
                "count": len(values),
            }

    category_tops = {}
    for col in categorical_cols:
        precomputed = aggregated_columns.get(col) if aggregated_columns else None
        if precomputed and precomputed.get("top_values"):
            category_tops[col] = precomputed.get("top_values", [])[:8]
            continue

        values = [str(row.get(col, "")) for row in rows if row.get(col) is not None]
        if values:
            counter = Counter(values)
            category_tops[col] = [{"label": key, "count": value} for key, value in counter.most_common(8)]

    executive_summary = {
        "total_rows": (precomputed_stats or {}).get("rows_after_dedup", len(rows)),
        "total_columns": len(schema),
        "numeric_count": len(numeric_cols),
        "categorical_count": len(categorical_cols),
        "date_count": len(date_cols),
        "numeric_stats": numeric_stats,
        "category_tops": category_tops,
    }

    # ── Distribution data ────────────────────────────────────────────
    distribution_data = []

    for col in numeric_cols:
        values = []
        for value in _sample_values(col):
            if value is None:
                continue
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                continue
        if not values:
            continue
        bins = _numeric_histogram(values)
        distribution_data.append({
            "column": col,
            "chart_type": "histogram",
            "labels": [b["label"] for b in bins],
            "data": [b["count"] for b in bins],
        })

    for col in categorical_cols:
        precomputed = aggregated_columns.get(col) if aggregated_columns else None
        if precomputed and precomputed.get("top_values"):
            top = [(item["label"], item["count"]) for item in precomputed.get("top_values", [])[:8]]
        else:
            vals = [str(row.get(col, "")) for row in rows if row.get(col) is not None]
            if not vals:
                continue
            counter = Counter(vals)
            top = counter.most_common(8)
        distribution_data.append({
            "column": col,
            "chart_type": "pie",
            "labels": [k for k, _ in top],
            "data": [v for _, v in top],
        })

    # ── Trend data (date × numeric) ──────────────────────────────────
    trend_data = []
    for date_col in date_cols:
        for num_col in numeric_cols[:3]:
            date_buckets = {}
            for row in rows:
                d = row.get(date_col)
                v = row.get(num_col)
                if d and v is not None:
                    try:
                        fv = float(v)
                        date_buckets.setdefault(str(d), []).append(fv)
                    except (ValueError, TypeError):
                        pass
            if not date_buckets:
                continue
            sorted_dates = sorted(date_buckets.keys())
            trend_data.append({
                "date_column": date_col,
                "value_column": num_col,
                "labels": sorted_dates,
                "data": [round(statistics.mean(date_buckets[d]), 2) for d in sorted_dates],
            })

    # ── Correlation pairs ────────────────────────────────────────────
    correlation_pairs = []
    for i, col_x in enumerate(numeric_cols):
        for col_y in numeric_cols[i + 1:]:
            points = []
            for row in rows[:200]:
                vx = row.get(col_x)
                vy = row.get(col_y)
                if vx is not None and vy is not None:
                    try:
                        points.append({"x": float(vx), "y": float(vy)})
                    except (ValueError, TypeError):
                        pass
            if len(points) >= 3:
                correlation_pairs.append({
                    "col_x": col_x,
                    "col_y": col_y,
                    "data": points,
                })

    # ── Advanced intelligence (insights, anomalies, forecasts) ──────
    auto_insights = []

    def _find_column(candidates, allow_contains=True):
        lowered = {str(col).strip().lower(): col for col in [c["column"] for c in schema]}
        for candidate in candidates:
            if candidate in lowered:
                return lowered[candidate]
        if allow_contains:
            for col in [c["column"] for c in schema]:
                token = str(col).strip().lower()
                if any(candidate in token for candidate in candidates):
                    return col
        return None

    def _safe_float(value):
        if value is None or isinstance(value, bool):
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

    shade_col = _find_column(("has_shade_trees", "shade_trees", "shade"))
    yield_col = _find_column(("yield_kg", "yield", "production", "tons_produced"))
    if shade_col and yield_col:
        no_shade_vals = []
        with_shade_vals = []
        for row in rows:
            category = str(row.get(shade_col, "")).strip().lower()
            yv = _safe_float(row.get(yield_col))
            if yv is None:
                continue
            if category in {"none", "no", "no shade", "without shade", "0", "false"}:
                no_shade_vals.append(yv)
            elif category in {"few", "many", "yes", "with shade", "shade", "1", "true"}:
                with_shade_vals.append(yv)
        if len(no_shade_vals) >= 2 and len(with_shade_vals) >= 2:
            no_shade_mean = statistics.mean(no_shade_vals)
            with_shade_mean = statistics.mean(with_shade_vals)
            if no_shade_mean < with_shade_mean:
                gap = round(with_shade_mean - no_shade_mean, 2)
                auto_insights.append(
                    {
                        "title": "Yield and Shade Trees",
                        "detail": f"Yield is lower in farms with no shade trees (average gap: {gap}).",
                        "confidence": "high",
                    }
                )

    if trend_data:
        first_trend = trend_data[0]
        if len(first_trend.get("data", [])) >= 3:
            deltas = [
                first_trend["data"][idx] - first_trend["data"][idx - 1]
                for idx in range(1, len(first_trend["data"]))
            ]
            avg_delta = statistics.mean(deltas) if deltas else 0
            trend_direction = "rising" if avg_delta > 0 else "declining" if avg_delta < 0 else "stable"
            auto_insights.append(
                {
                    "title": "Recent Trend Signal",
                    "detail": (
                        f"{first_trend['value_column']} is {trend_direction} over time based on uploaded records."
                    ),
                    "confidence": "medium",
                }
            )

    anomalies = []
    anomaly_threshold = 2.0
    for col in numeric_cols:
        values = []
        indexed_values = []
        for row_idx, row in enumerate(rows, start=1):
            fv = _safe_float(row.get(col))
            if fv is None:
                continue
            values.append(fv)
            indexed_values.append((row_idx, fv))
        if len(values) < 5:
            continue
        mean_v = statistics.mean(values)
        stdev_v = statistics.pstdev(values)
        if not stdev_v:
            continue
        for row_idx, fv in indexed_values:
            z_score = (fv - mean_v) / stdev_v
            if abs(z_score) >= anomaly_threshold:
                anomalies.append(
                    {
                        "column": col,
                        "row_number": row_idx,
                        "value": round(fv, 3),
                        "z_score": round(z_score, 2),
                        "severity": "high" if abs(z_score) >= 3.5 else "medium",
                    }
                )
    anomalies = sorted(anomalies, key=lambda item: abs(item["z_score"]), reverse=True)[:25]

    def _linear_forecast(series_labels, series_values, steps=3):
        if len(series_values) < 3:
            return None
        n = len(series_values)
        xs = list(range(n))
        mean_x = statistics.mean(xs)
        mean_y = statistics.mean(series_values)
        denom = sum((x - mean_x) ** 2 for x in xs)
        if not denom:
            return None
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, series_values)) / denom
        intercept = mean_y - slope * mean_x
        future = []
        for step in range(1, steps + 1):
            x_val = n - 1 + step
            prediction = intercept + slope * x_val
            future.append(
                {
                    "label": f"Next {step}",
                    "value": round(prediction, 3),
                }
            )
        return {
            "slope": round(slope, 4),
            "history_labels": series_labels,
            "history_values": [round(v, 3) for v in series_values],
            "forecast": future,
        }

    predictive_modeling = {
        "yield_forecast": None,
        "carbon_trend_forecast": None,
    }

    yield_trend = next(
        (item for item in trend_data if "yield" in str(item.get("value_column", "")).lower()),
        None,
    )
    carbon_trend = next(
        (
            item
            for item in trend_data
            if any(token in str(item.get("value_column", "")).lower() for token in ["emission", "carbon", "co2"])
        ),
        None,
    )
    if not yield_trend and trend_data:
        yield_trend = trend_data[0]
    if not carbon_trend:
        carbon_trend = yield_trend

    if yield_trend:
        predictive_modeling["yield_forecast"] = {
            "value_column": yield_trend.get("value_column"),
            "date_column": yield_trend.get("date_column"),
            "model": _linear_forecast(yield_trend.get("labels", []), yield_trend.get("data", [])),
        }

    if carbon_trend:
        predictive_modeling["carbon_trend_forecast"] = {
            "value_column": carbon_trend.get("value_column"),
            "date_column": carbon_trend.get("date_column"),
            "model": _linear_forecast(carbon_trend.get("labels", []), carbon_trend.get("data", [])),
        }

    return {
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "date_columns": date_cols,
        "executive_summary": executive_summary,
        "distribution_data": distribution_data,
        "trend_data": trend_data,
        "correlation_pairs": correlation_pairs,
        "auto_insights": auto_insights,
        "anomalies": anomalies,
        "predictive_modeling": predictive_modeling,
    }


def _default_analysis_state_for_dataset(dataset, dataset_analytics=None):
    numeric_columns = []
    if dataset_analytics:
        numeric_columns = list(dataset_analytics.get("numeric_columns") or [])

    return {
        "version": 1,
        "data_state": {
            "filters": [],
            "drill_through_context": [],
            "selected_metrics": numeric_columns[:3],
            "hierarchy_state": {},
            "slicers": {},
            "active_dataset_transformations": {
                "column_metadata": dataset.column_metadata or {},
                "row_operations": dataset.row_operations or {},
            },
        },
        "visualization_state": {
            "chart_types": {},
            "active_view": "charts",
        },
    }


def _normalize_analysis_state(raw_state, dataset, dataset_analytics=None):
    default_state = _default_analysis_state_for_dataset(dataset, dataset_analytics=dataset_analytics)
    if not isinstance(raw_state, dict):
        return default_state

    normalized = {
        "version": 1,
        "data_state": {},
        "visualization_state": {},
    }

    raw_data_state = raw_state.get("data_state") if isinstance(raw_state.get("data_state"), dict) else {}
    raw_viz_state = raw_state.get("visualization_state") if isinstance(raw_state.get("visualization_state"), dict) else {}

    filters = raw_data_state.get("filters")
    normalized["data_state"]["filters"] = filters if isinstance(filters, list) else []

    drill_ctx = raw_data_state.get("drill_through_context")
    normalized["data_state"]["drill_through_context"] = drill_ctx if isinstance(drill_ctx, list) else []

    selected_metrics = raw_data_state.get("selected_metrics")
    normalized["data_state"]["selected_metrics"] = selected_metrics if isinstance(selected_metrics, list) else default_state["data_state"]["selected_metrics"]

    hierarchy_state = raw_data_state.get("hierarchy_state")
    normalized["data_state"]["hierarchy_state"] = hierarchy_state if isinstance(hierarchy_state, dict) else {}

    slicers = raw_data_state.get("slicers")
    normalized["data_state"]["slicers"] = slicers if isinstance(slicers, dict) else {}

    normalized["data_state"]["active_dataset_transformations"] = {
        "column_metadata": dataset.column_metadata or {},
        "row_operations": dataset.row_operations or {},
    }

    chart_types = raw_viz_state.get("chart_types")
    normalized["visualization_state"]["chart_types"] = chart_types if isinstance(chart_types, dict) else {}
    normalized["visualization_state"]["active_view"] = str(raw_viz_state.get("active_view") or "charts")

    return normalized


def _build_partner_data_import_context(user, upload_form=None, preview_id=""):
    preview_batch = None
    if preview_id:
        preview_batch = InvestorDatasetImport.objects.filter(
            pk=preview_id,
            investor=user,
        ).first()

    if not preview_batch:
        preview_batch = InvestorDatasetImport.objects.filter(
            investor=user,
            status="draft",
        ).order_by("-created_at").first()

    preview_rows = []
    preview_columns = []
    active_schema = []
    if preview_batch:
        all_rows = [row.payload for row in preview_batch.rows.order_by("row_number")[:10000]]
        live_preview = LivePreviewGenerator.generate_preview(
            schema=preview_batch.schema or [],
            rows=all_rows,
            column_metadata=preview_batch.column_metadata or {},
            row_operations=preview_batch.row_operations or {},
        )
        active_schema = live_preview.get("schema") or []
        preview_columns = [item.get("column") for item in active_schema]
        for idx, row in enumerate((live_preview.get("rows") or [])[:20], start=1):
            preview_rows.append(
                {
                    "row_number": idx,
                    "values": [row.get(column) for column in preview_columns],
                }
            )

    if upload_form is None:
        upload_form = InvestorDatasetUploadForm()

    semantic_model = None
    if preview_batch:
        semantic_model = preview_batch.stats.get("semantic_model") if preview_batch.stats else None
        if not semantic_model:
            semantic_cache_key = _build_cache_key(
                "semantic_model",
                preview_batch.id,
                preview_batch.stats.get("rows_after_dedup", 0) if preview_batch.stats else 0,
            )
            semantic_model = cache.get(semantic_cache_key)
            if semantic_model is None:
                semantic_model = build_dynamic_semantic_model(
                    dataset_schema=preview_batch.schema or [],
                    dataset_rows=[row.payload for row in preview_batch.rows.order_by("row_number")[:300]],
                    investor=user,
                )
                cache.set(semantic_cache_key, semantic_model, ANALYTICS_CACHE_TTL_SECONDS)

    dataset_analytics = None
    if preview_batch and preview_batch.schema:
        analytics_cache_key = _build_cache_key(
            "dataset_analytics",
            preview_batch.id,
            preview_batch.stats.get("rows_after_dedup", 0) if preview_batch.stats else 0,
        )
        dataset_analytics = cache.get(analytics_cache_key)
        if dataset_analytics is None:
            dataset_analytics = _build_dataset_analytics(
                schema=preview_batch.schema,
                rows_qs=preview_batch.rows,
                precomputed_stats=preview_batch.stats,
            )
            cache.set(analytics_cache_key, dataset_analytics, ANALYTICS_CACHE_TTL_SECONDS)

    initial_analysis_state = {}
    if preview_batch:
        stored_engine_state = (preview_batch.prep_state or {}).get("analytics_engine")
        initial_analysis_state = _normalize_analysis_state(
            stored_engine_state,
            preview_batch,
            dataset_analytics=dataset_analytics,
        )

    saved_imports = InvestorDatasetImport.objects.filter(
        investor=user,
    )[:20]

    investor_profile = UserProfile.objects.filter(user=user).first()

    return {
        "upload_form": upload_form,
        "preview_batch": preview_batch,
        "preview_rows": preview_rows,
        "preview_columns": preview_columns,
        "active_schema": active_schema,
        "semantic_model": semantic_model,
        "dataset_analytics": dataset_analytics,
        "initial_analysis_state": initial_analysis_state,
        "investor_profile": investor_profile,
        "saved_dashboard_layout": (investor_profile.dashboard_layout if investor_profile else {}),
        "saved_imports": saved_imports,
        "recent_imports": InvestorDatasetImport.objects.filter(
            investor=user,
            status="imported",
        )[:5],
    }


@login_required
def dataset_analysis_mode_selector(request):
    """
    Show decision page asking partner to choose between integrated or standalone analysis.
    
    GET params:
        - dataset_id: ID of the newly uploaded InvestorDatasetImport
    
    POST params:
        - dataset_id: ID of the dataset
        - analysis_mode: 'integrated' or 'standalone'
    """
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")

    if request.method == "POST":
        dataset_id = request.POST.get("dataset_id", "").strip()
        analysis_mode = request.POST.get("analysis_mode", "").strip()
        
        if not dataset_id or analysis_mode not in {"integrated", "standalone"}:
            messages.error(request, "Invalid selection. Please try again.")
            return redirect("partner_external_analysis")
        
        try:
            dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
        except InvestorDatasetImport.DoesNotExist:
            messages.error(request, "Dataset not found.")
            return redirect("partner_external_analysis")
        
        # Store mode choice in session for this dataset
        if "analysis_modes" not in request.session:
            request.session["analysis_modes"] = {}
        request.session["analysis_modes"][str(dataset_id)] = analysis_mode
        request.session.modified = True
        
        _log_dataset_audit(
            actor=request.user,
            dataset=dataset,
            action="select_analysis_mode",
            details={"analysis_mode": analysis_mode},
        )
        
        if analysis_mode == "integrated":
            return redirect(f"{reverse('partner_external_analysis')}?preview_id={dataset_id}")
        else:  # standalone
            return redirect(f"{reverse('partner_standalone_analysis')}?preview_id={dataset_id}")
    
    # GET request: show decision page
    dataset_id = request.GET.get("dataset_id", "").strip()
    
    if not dataset_id:
        messages.error(request, "No dataset specified.")
        return redirect("partner_external_analysis")
    
    try:
        dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
    except InvestorDatasetImport.DoesNotExist:
        messages.error(request, "Dataset not found.")
        return redirect("partner_external_analysis")
    
    context = {
        "dataset": dataset,
        "dataset_id": dataset_id,
    }
    return render(request, "Farmers/dataset_analysis_mode_selector.html", context)


@login_required
def partner_standalone_analysis(request):
    """
    Standalone data analysis page with no farm portfolio references.
    Shows only the uploaded dataset analysis tools and visualizations.
    """
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied

    context = _build_partner_data_import_context(
        request.user,
        preview_id=request.GET.get("preview_id", ""),
    )
    # Mark this as standalone mode so template can exclude portfolio sections
    context["standalone_mode"] = True
    return render(request, "Farmers/partner_standalone_analysis.html", context)


@login_required
def partner_external_analysis(request):
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied

    context = _build_partner_data_import_context(
        request.user,
        preview_id=request.GET.get("preview_id", ""),
    )
    return render(request, "Farmers/partner_external_analysis.html", context)


@login_required
def partner_external_dataset_intelligence(request):
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied

    context = _build_partner_data_import_context(
        request.user,
        preview_id=request.GET.get("preview_id", ""),
    )
    context["external_dataset_intelligence_mode"] = True
    return render(request, "Farmers/partner_external_analysis.html", context)


@login_required
def partner_field_agent_data_center(request):
    if not _user_has_role(request.user, {"investor", "analyst", "admin"}):
        return HttpResponseForbidden("Access Denied")
    return redirect(f"{reverse('partner_dashboard')}?view=field-agent-data-center")


@login_required
def partner_api_dataset_ingest(request):
    """API ingestion endpoint for JSON payloads with bulk/incremental modes."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid JSON body"}, status=400)

    rows = payload.get("rows") or payload.get("data")
    if not isinstance(rows, list) or not rows:
        return JsonResponse({"ok": False, "error": "rows/data array is required"}, status=400)

    mode = str(payload.get("mode") or "bulk").strip().lower()
    if mode not in {"bulk", "incremental"}:
        return JsonResponse({"ok": False, "error": "mode must be 'bulk' or 'incremental'"}, status=400)

    dataset_name = str(payload.get("dataset_name") or "API Dataset Upload").strip() or "API Dataset Upload"
    source_label = str(payload.get("source") or "api").strip().lower()
    synthetic_filename = f"{dataset_name.replace(' ', '_').lower()}_{uuid.uuid4().hex[:8]}.json"

    if mode == "incremental":
        dataset_id = str(payload.get("dataset_id") or "").strip()
        if not dataset_id:
            return JsonResponse({"ok": False, "error": "dataset_id is required for incremental mode"}, status=400)
        try:
            dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
        except InvestorDatasetImport.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Dataset not found"}, status=404)

        existing_rows = list(dataset.rows.order_by("row_number").values_list("payload", flat=True))
        merged_rows = existing_rows + [row for row in rows if isinstance(row, dict)]
        merged_bytes = json.dumps(merged_rows, default=str).encode("utf-8")

        try:
            parsed_dataset = parse_and_clean_dataset(merged_bytes, synthetic_filename)
        except DatasetImportError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)

        with transaction.atomic():
            stats_payload = dict(parsed_dataset["stats"])
            stats_payload["ingestion_mode"] = "incremental"
            stats_payload["ingestion_source"] = source_label

            semantic_model = build_dynamic_semantic_model(
                dataset_schema=parsed_dataset["schema"],
                dataset_rows=parsed_dataset["rows"][:400],
                investor=request.user,
            )
            stats_payload["semantic_model"] = semantic_model

            dataset.schema = parsed_dataset["schema"]
            dataset.stats = stats_payload
            dataset.file_format = "json"
            dataset.source_file.save(synthetic_filename, ContentFile(merged_bytes), save=False)
            dataset.save(update_fields=["schema", "stats", "file_format", "source_file"])

            dataset.rows.all().delete()
            row_batch = []
            for index, row in enumerate(parsed_dataset["rows"]):
                row_batch.append(
                    InvestorDatasetRow(
                        dataset=dataset,
                        row_number=index + 1,
                        payload=row,
                        fingerprint=json.dumps(row, sort_keys=True, default=str),
                    )
                )
                if len(row_batch) >= ROW_BULK_CREATE_BATCH_SIZE:
                    InvestorDatasetRow.objects.bulk_create(row_batch, batch_size=ROW_BULK_CREATE_BATCH_SIZE)
                    row_batch = []
            if row_batch:
                InvestorDatasetRow.objects.bulk_create(row_batch, batch_size=ROW_BULK_CREATE_BATCH_SIZE)

            _log_dataset_audit(
                actor=request.user,
                dataset=dataset,
                action="incremental_upload",
                details={
                    "dataset_name": dataset.dataset_name,
                    "ingestion_source": source_label,
                    "rows_after_dedup": parsed_dataset["stats"].get("rows_after_dedup", 0),
                },
            )

        return JsonResponse(
            {
                "ok": True,
                "mode": "incremental",
                "dataset_id": dataset.id,
                "dataset_name": dataset.dataset_name,
                "rows_after_dedup": parsed_dataset["stats"].get("rows_after_dedup", 0),
                "ai_summary": parsed_dataset["stats"].get("ai_investment_insight_summary"),
            }
        )

    clean_rows = [row for row in rows if isinstance(row, dict)]
    if not clean_rows:
        return JsonResponse({"ok": False, "error": "No object rows found for ingestion"}, status=400)

    payload_bytes = json.dumps(clean_rows, default=str).encode("utf-8")
    try:
        parsed_dataset = parse_and_clean_dataset(payload_bytes, synthetic_filename)
    except DatasetImportError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    with transaction.atomic():
        semantic_model = build_dynamic_semantic_model(
            dataset_schema=parsed_dataset["schema"],
            dataset_rows=parsed_dataset["rows"][:400],
            investor=request.user,
        )
        stats_payload = dict(parsed_dataset["stats"])
        stats_payload["semantic_model"] = semantic_model
        stats_payload["ingestion_mode"] = "bulk"
        stats_payload["ingestion_source"] = source_label

        draft = InvestorDatasetImport(
            investor=request.user,
            dataset_name=dataset_name,
            file_format="json",
            schema=parsed_dataset["schema"],
            stats=stats_payload,
            status="draft",
        )
        draft.source_file.save(synthetic_filename, ContentFile(payload_bytes), save=False)
        draft.save()

        domain_classification = detect_dataset_domain(
            dataset_schema=parsed_dataset["schema"],
            dataset_rows=parsed_dataset["rows"][:100],
        )
        draft.inferred_domain = domain_classification["inferred_domain"]
        draft.inferred_domain_scores = domain_classification["domain_scores"]
        draft.inferred_domain_confidence = domain_classification["confidence"]
        draft.save(update_fields=["inferred_domain", "inferred_domain_scores", "inferred_domain_confidence"])

        row_batch = []
        for index, row in enumerate(parsed_dataset["rows"]):
            row_batch.append(
                InvestorDatasetRow(
                    dataset=draft,
                    row_number=index + 1,
                    payload=row,
                    fingerprint=json.dumps(row, sort_keys=True, default=str),
                )
            )
            if len(row_batch) >= ROW_BULK_CREATE_BATCH_SIZE:
                InvestorDatasetRow.objects.bulk_create(row_batch, batch_size=ROW_BULK_CREATE_BATCH_SIZE)
                row_batch = []
        if row_batch:
            InvestorDatasetRow.objects.bulk_create(row_batch, batch_size=ROW_BULK_CREATE_BATCH_SIZE)

        _log_dataset_audit(
            actor=request.user,
            dataset=draft,
            action="api_ingest",
            details={
                "dataset_name": dataset_name,
                "ingestion_source": source_label,
                "rows_after_dedup": parsed_dataset["stats"].get("rows_after_dedup", 0),
            },
        )

    return JsonResponse(
        {
            "ok": True,
            "mode": "bulk",
            "dataset_id": draft.id,
            "dataset_name": draft.dataset_name,
            "rows_after_dedup": parsed_dataset["stats"].get("rows_after_dedup", 0),
            "ai_summary": parsed_dataset["stats"].get("ai_investment_insight_summary"),
            "next": f"{reverse('dataset_analysis_mode_selector')}?dataset_id={draft.id}",
        }
    )


@login_required
def dataset_audit_log_viewer(request):
    if not _user_has_role(request.user, {"admin", "analyst"}):
        return HttpResponseForbidden("Access Denied")

    action = (request.GET.get("action") or "").strip()
    actor_query = (request.GET.get("actor") or "").strip()
    start_date_raw = (request.GET.get("start_date") or "").strip()
    end_date_raw = (request.GET.get("end_date") or "").strip()
    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date
        start_date_raw = start_date.isoformat()
        end_date_raw = end_date.isoformat()

    logs = DatasetAuditLog.objects.select_related("actor", "dataset").all()
    valid_actions = {choice[0] for choice in DatasetAuditLog.ACTION_CHOICES}
    if action in valid_actions:
        logs = logs.filter(action=action)
    else:
        action = ""

    if actor_query:
        logs = logs.filter(actor__username__icontains=actor_query)

    if start_date:
        logs = logs.filter(created_at__date__gte=start_date)
    if end_date:
        logs = logs.filter(created_at__date__lte=end_date)

    paginator = Paginator(logs, AUDIT_LOG_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]
    query_string = query_params.urlencode()

    return render(
        request,
        "Farmers/dataset_audit_logs.html",
        {
            "logs": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": page_obj.has_other_pages(),
            "action_choices": DatasetAuditLog.ACTION_CHOICES,
            "selected_action": action,
            "actor_query": actor_query,
            "start_date": start_date_raw,
            "end_date": end_date_raw,
            "query_string": query_string,
        },
    )


@login_required
def partner_dataset_upload(request):
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")

    if request.method != "POST":
        return redirect("partner_external_analysis")

    action = request.POST.get("action", "preview")

    if action == "save_layout":
        layout_payload = (request.POST.get("layout_payload") or "").strip()
        try:
            parsed_layout = json.loads(layout_payload or "{}")
        except json.JSONDecodeError:
            messages.error(request, "Could not save layout. Please try again.")
            return redirect("partner_external_analysis")

        if not isinstance(parsed_layout, dict):
            messages.error(request, "Could not save layout. Invalid layout format.")
            return redirect("partner_external_analysis")

        expected_zones = {"top", "middle", "bottom"}
        normalized_layout = {}
        for zone in expected_zones:
            zone_items = parsed_layout.get(zone, [])
            if not isinstance(zone_items, list):
                zone_items = []
            normalized_layout[zone] = [str(item) for item in zone_items if isinstance(item, str)][:30]

        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile or profile.role not in {"investor", "analyst"}:
            return HttpResponseForbidden("Access Denied")

        profile.dashboard_layout = normalized_layout
        profile.save(update_fields=["dashboard_layout"])
        _log_dataset_audit(
            actor=request.user,
            action="save_layout",
            details={"zones": {k: len(v) for k, v in normalized_layout.items()}},
        )
        messages.success(request, "Your dashboard layout has been saved.")
        return redirect("partner_external_analysis")

    if action in {"import", "discard", "load_existing", "delete_existing"}:
        batch_id = request.POST.get("batch_id")
        batch = get_object_or_404(
            InvestorDatasetImport,
            pk=batch_id,
            investor=request.user,
        )

        if action in {"import", "discard"} and batch.status != "draft":
            messages.error(request, "Only draft dataset previews can be imported or discarded.")
            return redirect("partner_external_analysis")

        if action == "load_existing":
            _log_dataset_audit(
                actor=request.user,
                dataset=batch,
                action="load_existing",
                details={"dataset_name": batch.dataset_name},
            )
            return redirect(f"{reverse('partner_external_analysis')}?preview_id={batch.id}")

        if action == "delete_existing":
            current_preview_id = request.POST.get("current_preview_id", "")
            deleted_dataset_name = batch.dataset_name
            deleted_dataset_id = batch.id
            if batch.source_file:
                batch.source_file.delete(save=False)
            batch.delete()
            _log_dataset_audit(
                actor=request.user,
                action="delete",
                details={"dataset_id": deleted_dataset_id, "dataset_name": deleted_dataset_name},
            )
            messages.success(request, "Dataset deleted.")
            if current_preview_id and str(current_preview_id) != str(batch_id):
                return redirect(f"{reverse('partner_external_analysis')}?preview_id={current_preview_id}")
            return redirect("partner_external_analysis")

        if action == "discard":
            discarded_name = batch.dataset_name
            discarded_id = batch.id
            batch.delete()
            _log_dataset_audit(
                actor=request.user,
                action="discard",
                details={"dataset_id": discarded_id, "dataset_name": discarded_name},
            )
            messages.info(request, "Draft dataset preview discarded.")
            return redirect("partner_external_analysis")

        batch.status = "imported"
        batch.imported_at = timezone.now()
        batch.save(update_fields=["status", "imported_at"])
        _log_dataset_audit(
            actor=request.user,
            dataset=batch,
            action="import",
            details={"dataset_name": batch.dataset_name, "rows": batch.stats.get("rows_after_dedup", 0) if batch.stats else 0},
        )
        imported_count = batch.stats.get("rows_after_dedup", batch.rows.count()) if batch.stats else batch.rows.count()
        messages.success(request, f"Dataset '{batch.dataset_name}' imported successfully with {imported_count} clean rows.")
        return redirect("partner_external_analysis")

    form = InvestorDatasetUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        context = _build_partner_data_import_context(request.user, upload_form=form)
        return render(request, "Farmers/partner_external_analysis.html", context)

    uploaded_file = form.cleaned_data["data_file"]
    uploaded_bytes = uploaded_file.read()

    try:
        parsed_dataset = parse_and_clean_dataset(uploaded_bytes, uploaded_file.name)
    except DatasetImportError as exc:
        form.add_error("data_file", str(exc))
        context = _build_partner_data_import_context(request.user, upload_form=form)
        return render(request, "Farmers/partner_external_analysis.html", context)

    # ── Data Reduction: apply drop options from the UI ──────────────
    rows = parsed_dataset["rows"]
    schema = parsed_dataset["schema"]

    # 1. Drop columns by name
    drop_cols_raw = request.POST.get("drop_columns", "").strip()
    if drop_cols_raw:
        cols_to_drop = {c.strip() for c in drop_cols_raw.split(",") if c.strip()}
        if cols_to_drop:
            rows = [{k: v for k, v in row.items() if k not in cols_to_drop} for row in rows]
            schema = [col for col in schema if col.get("column") not in cols_to_drop]

    # 2. Drop columns that are entirely empty
    if request.POST.get("drop_all_missing_cols") == "1" and rows:
        all_keys = {k for row in rows for k in row}
        non_empty_cols = {k for k in all_keys if any(row.get(k) not in (None, "", []) for row in rows)}
        rows = [{k: v for k, v in row.items() if k in non_empty_cols} for row in rows]
        schema = [col for col in schema if col.get("column") in non_empty_cols]

    # 3. Drop rows with any missing values
    if request.POST.get("drop_missing_rows") == "1":
        rows = [row for row in rows if all(v not in (None, "") for v in row.values())]

    # 4. Drop rows matching a condition
    drop_row_col = request.POST.get("drop_row_col", "").strip()
    drop_row_op = request.POST.get("drop_row_op", "").strip()
    drop_row_value = request.POST.get("drop_row_value", "").strip()
    if drop_row_col and drop_row_op:
        def _matches_drop(row):
            cell = str(row.get(drop_row_col, ""))
            if drop_row_op == "equals":
                return cell == drop_row_value
            if drop_row_op == "not_equals":
                return cell != drop_row_value
            if drop_row_op == "contains":
                return drop_row_value.lower() in cell.lower()
            if drop_row_op == "greater_than":
                try:
                    return float(cell) > float(drop_row_value)
                except (ValueError, TypeError):
                    return False
            if drop_row_op == "less_than":
                try:
                    return float(cell) < float(drop_row_value)
                except (ValueError, TypeError):
                    return False
            if drop_row_op == "is_empty":
                return cell in ("", "None", "nan")
            if drop_row_op == "is_not_empty":
                return cell not in ("", "None", "nan")
            return False
        rows = [row for row in rows if not _matches_drop(row)]

    # Update parsed_dataset with reduced data
    parsed_dataset = dict(parsed_dataset)
    parsed_dataset["rows"] = rows
    parsed_dataset["schema"] = schema
    parsed_dataset["stats"] = dict(parsed_dataset["stats"])
    parsed_dataset["stats"]["rows_after_dedup"] = len(rows)
    # ─────────────────────────────────────────────────────────────────

    dataset_name = (form.cleaned_data.get("dataset_name") or "").strip()
    if not dataset_name:
        dataset_name = uploaded_file.name.rsplit(".", 1)[0]

    with transaction.atomic():
        semantic_model = build_dynamic_semantic_model(
            dataset_schema=parsed_dataset["schema"],
            dataset_rows=parsed_dataset["rows"][:400],
            investor=request.user,
        )

        stats_payload = dict(parsed_dataset["stats"])
        stats_payload["semantic_model"] = semantic_model

        draft = InvestorDatasetImport(
            investor=request.user,
            dataset_name=dataset_name,
            file_format=parsed_dataset["file_format"],
            schema=parsed_dataset["schema"],
            stats=stats_payload,
            status="draft",
        )
        draft.source_file.save(uploaded_file.name, ContentFile(uploaded_bytes), save=False)
        draft.save()
        
        # Detect and classify dataset domain
        domain_classification = detect_dataset_domain(
            dataset_schema=parsed_dataset["schema"],
            dataset_rows=parsed_dataset["rows"][:100],
        )
        draft.inferred_domain = domain_classification["inferred_domain"]
        draft.inferred_domain_scores = domain_classification["domain_scores"]
        draft.inferred_domain_confidence = domain_classification["confidence"]
        draft.save(
            update_fields=[
                "inferred_domain",
                "inferred_domain_scores",
                "inferred_domain_confidence",
                "source_file",
                "dataset_name",
                "file_format",
                "schema",
                "stats",
                "status",
            ]
        )

        _log_dataset_audit(
            actor=request.user,
            dataset=draft,
            action="upload_preview",
            details={
                "dataset_name": dataset_name,
                "file_format": parsed_dataset["file_format"],
                "rows_after_dedup": parsed_dataset["stats"].get("rows_after_dedup", 0),
                "inferred_domain": domain_classification["inferred_domain"],
            },
        )

        row_batch = []
        for index, row in enumerate(parsed_dataset["rows"]):
            row_batch.append(
                InvestorDatasetRow(
                    dataset=draft,
                    row_number=index + 1,
                    payload=row,
                    fingerprint=json.dumps(row, sort_keys=True, default=str),
                )
            )
            if len(row_batch) >= ROW_BULK_CREATE_BATCH_SIZE:
                InvestorDatasetRow.objects.bulk_create(row_batch, batch_size=ROW_BULK_CREATE_BATCH_SIZE)
                row_batch = []

        if row_batch:
            InvestorDatasetRow.objects.bulk_create(row_batch, batch_size=ROW_BULK_CREATE_BATCH_SIZE)

    preview_count = parsed_dataset["stats"].get("rows_after_dedup", 0)
    duplicate_count = parsed_dataset["stats"].get("duplicate_rows_removed", 0)
    messages.info(
        request,
        f"Preview ready for '{dataset_name}'. {preview_count} clean rows prepared ({duplicate_count} duplicates removed).",
    )
    return redirect(f"{reverse('dataset_analysis_mode_selector')}?dataset_id={draft.id}")


@login_required
def confirm_dataset_domain_classification(request):
    """
    AJAX endpoint to confirm or override dataset domain classification.
    
    POST params:
        - dataset_id: ID of the InvestorDatasetImport
        - confirmed_domain: The domain choice (agriculture, finance, hr, inventory, carbon_esg, general, custom)
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)
    
    dataset_id = request.POST.get("dataset_id", "").strip()
    confirmed_domain = request.POST.get("confirmed_domain", "").strip()
    
    if not dataset_id or not confirmed_domain:
        return JsonResponse(
            {"ok": False, "error": "dataset_id and confirmed_domain are required"},
            status=400,
        )
    
    try:
        dataset = InvestorDatasetImport.objects.get(
            pk=dataset_id,
            investor=request.user,
        )
    except InvestorDatasetImport.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": "Dataset not found"},
            status=404,
        )
    
    # Validate the confirmed domain
    valid_domains = {choice[0] for choice in InvestorDatasetImport.DOMAIN_CHOICES}
    if confirmed_domain not in valid_domains:
        return JsonResponse(
            {"ok": False, "error": f"Invalid domain: {confirmed_domain}"},
            status=400,
        )
    
    dataset.confirmed_domain = confirmed_domain
    dataset.save(update_fields=["confirmed_domain"])
    
    _log_dataset_audit(
        actor=request.user,
        dataset=dataset,
        action="upload_preview",
        details={
            "action": "confirm_domain_classification",
            "inferred_domain": dataset.inferred_domain,
            "confirmed_domain": confirmed_domain,
        },
    )
    
    return JsonResponse({
        "ok": True,
        "message": f"Domain classification confirmed: {confirmed_domain}",
        "confirmed_domain": confirmed_domain,
    })


@login_required
def dataset_analysis_state(request):
    """Persist or retrieve analysis state decoupled from visualization rendering."""
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)

    if request.method == "GET":
        dataset_id = (request.GET.get("dataset_id") or "").strip()
    elif request.method == "POST":
        dataset_id = (request.POST.get("dataset_id") or "").strip()
    else:
        return JsonResponse({"ok": False, "error": "GET or POST required"}, status=405)

    if not dataset_id:
        return JsonResponse({"ok": False, "error": "dataset_id is required"}, status=400)

    try:
        dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
    except InvestorDatasetImport.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Dataset not found"}, status=404)

    analytics_payload = None
    if dataset.schema:
        analytics_payload = _build_dataset_analytics(
            schema=dataset.schema,
            rows_qs=dataset.rows,
            precomputed_stats=dataset.stats,
        )

    prep_state = dict(dataset.prep_state or {})

    if request.method == "GET":
        normalized = _normalize_analysis_state(
            prep_state.get("analytics_engine"),
            dataset,
            dataset_analytics=analytics_payload,
        )
        return JsonResponse({"ok": True, "state": normalized})

    raw_state = (request.POST.get("state") or "").strip()
    if not raw_state:
        return JsonResponse({"ok": False, "error": "state is required"}, status=400)

    try:
        parsed_state = json.loads(raw_state)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "state must be valid JSON"}, status=400)

    normalized = _normalize_analysis_state(
        parsed_state,
        dataset,
        dataset_analytics=analytics_payload,
    )
    prep_state["analytics_engine"] = normalized
    dataset.prep_state = prep_state
    dataset.save(update_fields=["prep_state"])

    return JsonResponse({"ok": True, "state": normalized})


# -----------------------------------------------------------------------
# Data Preparation Workspace
# -----------------------------------------------------------------------
@login_required
def data_prep_workspace(request):
    """Render the interactive data preparation workspace."""
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")
    
    preview_id = request.GET.get("preview_id", "").strip()
    dataset = None
    
    if preview_id:
        try:
            dataset = InvestorDatasetImport.objects.get(pk=preview_id, investor=request.user)
        except InvestorDatasetImport.DoesNotExist:
            pass
    
    if not dataset:
        messages.error(request, "Dataset not found.")
        return redirect("partner_external_analysis")
    
    # Get current prep state
    prep_state = dataset.prep_state or {}
    column_metadata = dataset.column_metadata or {}
    row_operations = dataset.row_operations or {}
    prep_history = DataPrepHistory(dataset.prep_history or [])
    
    # Get all rows (up to 10000 for performance)
    all_rows = list(dataset.rows.all().values_list("payload", flat=True)[:10000])
    
    # Generate live preview
    preview = LivePreviewGenerator.generate_preview(
        schema=dataset.schema,
        rows=all_rows,
        column_metadata=column_metadata,
        row_operations=row_operations,
    )
    
    # Get first 50 rows for display
    preview_rows = preview["rows"][:50]
    
    context = {
        "dataset": dataset,
        "schema": dataset.schema,
        "column_metadata": column_metadata,
        "row_operations": row_operations,
        "preview": preview,
        "preview_rows": preview_rows,
        "prep_history_count": len(dataset.prep_history or []),
        "can_undo": prep_history.can_undo(),
        "can_redo": prep_history.can_redo(),
    }
    
    return render(request, "Farmers/data_prep_workspace.html", context)


# -----------------------------------------------------------------------
# Multi-Dataset Analytics
# -----------------------------------------------------------------------

_PLATFORM_DATASETS = [
    {
        "id": "platform_farms",
        "name": "Platform Farm Records",
        "status": "platform",
        "domain": "agriculture",
        "columns": ["farmer_id", "farm_id", "region", "area_hectares", "carbon_score", "yield_estimate"],
        "row_count": None,
        "created_at": None,
        "is_session": False,
    },
    {
        "id": "platform_carbon",
        "name": "Platform Carbon Data",
        "status": "platform",
        "domain": "carbon_esg",
        "columns": ["farmer_id", "farm_id", "carbon_credits", "verification_date", "sequestration_tonnes"],
        "row_count": None,
        "created_at": None,
        "is_session": False,
    },
]


@login_required
def partner_dataset_list(request):
    """Return a JSON list of all datasets owned by the requesting user plus platform datasets."""
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)

    datasets = InvestorDatasetImport.objects.filter(investor=request.user).order_by("-created_at")[:50]
    result = []
    for ds in datasets:
        schema = ds.schema or []
        columns = _schema_column_names(schema)
        result.append({
            "id": ds.id,
            "name": ds.dataset_name,
            "status": ds.status,
            "domain": ds.confirmed_domain or ds.inferred_domain or "general",
            "columns": columns,
            "row_count": ds.rows.count(),
            "created_at": ds.created_at.isoformat(),
            "is_session": ds.status == "draft",
        })

    return JsonResponse({"ok": True, "datasets": result + _PLATFORM_DATASETS})


@login_required
def partner_dataset_join_suggest(request):
    """Suggest join keys between two datasets based on column name matching."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)

    dataset_a_id = (request.POST.get("dataset_a") or "").strip()
    dataset_b_id = (request.POST.get("dataset_b") or "").strip()

    if not dataset_a_id or not dataset_b_id:
        return JsonResponse({"ok": False, "error": "dataset_a and dataset_b are required"}, status=400)

    platform_cols = {ds["id"]: ds["columns"] for ds in _PLATFORM_DATASETS}

    def get_columns(ds_id):
        if ds_id in platform_cols:
            return platform_cols[ds_id]
        try:
            ds = InvestorDatasetImport.objects.get(pk=ds_id, investor=request.user)
            return _schema_column_names(ds.schema)
        except (InvestorDatasetImport.DoesNotExist, ValueError):
            return []

    cols_a = get_columns(dataset_a_id)
    cols_b = get_columns(dataset_b_id)

    if not cols_a or not cols_b:
        return JsonResponse({"ok": False, "error": "One or both datasets not found or have no columns"}, status=404)

    set_a = set(cols_a)
    set_b = set(cols_b)

    # Exact name matches (case-insensitive normalised).
    exact = sorted(set_a & set_b)
    suggestions = [{"col_a": col, "col_b": col, "confidence": "high"} for col in exact]

    # Fuzzy: ID-like columns whose base name matches.
    id_pattern = re.compile(r"(_id|_key|_code|_num|id$|key$)", re.IGNORECASE)
    fuzzy_seen = set()
    for col_a in set_a:
        if not id_pattern.search(col_a):
            continue
        for col_b in set_b:
            if not id_pattern.search(col_b) or col_a == col_b:
                continue
            pair_key = tuple(sorted([col_a, col_b]))
            if pair_key in fuzzy_seen:
                continue
            base_a = id_pattern.sub("", col_a).lower().strip("_")
            base_b = id_pattern.sub("", col_b).lower().strip("_")
            if base_a and base_b and (base_a == base_b or base_a in base_b or base_b in base_a):
                fuzzy_seen.add(pair_key)
                suggestions.append({"col_a": col_a, "col_b": col_b, "confidence": "medium"})

    return JsonResponse({
        "ok": True,
        "suggestions": suggestions[:10],
        "cols_a": sorted(cols_a),
        "cols_b": sorted(cols_b),
    })


@login_required
def data_prep_column_operation(request):
    """Handle column operations (rename, retype, hide, semantic tag, remove)."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)
    
    dataset_id = request.POST.get("dataset_id", "").strip()
    operation = request.POST.get("operation", "").strip()
    column_name = request.POST.get("column_name", "").strip()
    
    try:
        dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
    except InvestorDatasetImport.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Dataset not found"}, status=404)
    
    column_metadata = dataset.column_metadata or {}
    prep_history = DataPrepHistory(dataset.prep_history or [])
    
    try:
        if operation == "rename":
            new_name = request.POST.get("new_name", "").strip()
            if not new_name:
                raise ValueError("new_name is required")
            ColumnOperations.rename_column(column_metadata, column_name, new_name)
            
        elif operation == "retype":
            new_type = request.POST.get("new_type", "").strip()
            if not new_type:
                raise ValueError("new_type is required")
            ColumnOperations.retype_column(column_metadata, column_name, new_type)
            
        elif operation == "hide":
            hidden = request.POST.get("hidden", "false").lower() == "true"
            ColumnOperations.hide_column(column_metadata, column_name, hidden)
            
        elif operation == "semantic_tag":
            semantic_tag = request.POST.get("semantic_tag", "").strip()
            if not semantic_tag:
                raise ValueError("semantic_tag is required")
            ColumnOperations.tag_column_semantic(column_metadata, column_name, semantic_tag)
            
        elif operation == "remove":
            ColumnOperations.remove_column(column_metadata, column_name)
            
        else:
            return JsonResponse({"ok": False, "error": f"Unknown operation: {operation}"}, status=400)
        
        # Save changes
        dataset.column_metadata = column_metadata
        prep_history.add_operation(operation, {
            "column": column_name,
            "operation": operation,
            "metadata": column_metadata.copy(),
        })
        dataset.prep_history = prep_history.serialize()
        dataset.save(update_fields=["column_metadata", "prep_history"])
        
        # Generate updated preview
        all_rows = list(dataset.rows.all().values_list("payload", flat=True)[:10000])
        preview = LivePreviewGenerator.generate_preview(
            schema=dataset.schema,
            rows=all_rows,
            column_metadata=column_metadata,
            row_operations=dataset.row_operations or {},
        )
        
        return JsonResponse({
            "ok": True,
            "operation": operation,
            "column": column_name,
            "column_metadata": column_metadata,
            "preview": preview,
        })
        
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@login_required
def data_prep_row_operation(request):
    """Handle row operations (remove, filter, exclude nulls, dedup)."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)
    
    dataset_id = request.POST.get("dataset_id", "").strip()
    operation = request.POST.get("operation", "").strip()
    
    try:
        dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
    except InvestorDatasetImport.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Dataset not found"}, status=404)
    
    row_operations = dataset.row_operations or {}
    prep_history = DataPrepHistory(dataset.prep_history or [])
    
    try:
        if operation == "remove_rows":
            row_numbers_str = request.POST.get("row_numbers", "").strip()
            row_numbers = [int(x.strip()) for x in row_numbers_str.split(",") if x.strip()]
            RowOperations.remove_rows(row_operations, row_numbers)
            
        elif operation == "add_filter":
            column = request.POST.get("column", "").strip()
            op = request.POST.get("operator", "").strip()
            value = request.POST.get("value", "")
            RowOperations.apply_filter(row_operations, column, op, value)
            
        elif operation == "exclude_nulls":
            columns_str = request.POST.get("columns", "").strip()
            columns = [x.strip() for x in columns_str.split(",") if x.strip()]
            RowOperations.exclude_nulls(row_operations, columns)
            
        elif operation == "remove_duplicates":
            key_cols_str = request.POST.get("key_columns", "").strip()
            key_cols = [x.strip() for x in key_cols_str.split(",") if x.strip()] if key_cols_str else None
            RowOperations.remove_duplicates(row_operations, key_cols)
            
        else:
            return JsonResponse({"ok": False, "error": f"Unknown operation: {operation}"}, status=400)
        
        # Save changes
        dataset.row_operations = row_operations
        prep_history.add_operation(operation, {
            "operation": operation,
            "row_operations": row_operations.copy(),
        })
        dataset.prep_history = prep_history.serialize()
        dataset.save(update_fields=["row_operations", "prep_history"])
        
        # Generate updated preview
        all_rows = list(dataset.rows.all().values_list("payload", flat=True)[:10000])
        preview = LivePreviewGenerator.generate_preview(
            schema=dataset.schema,
            rows=all_rows,
            column_metadata=dataset.column_metadata or {},
            row_operations=row_operations,
        )
        
        return JsonResponse({
            "ok": True,
            "operation": operation,
            "row_operations": row_operations,
            "preview": preview,
        })
        
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@login_required
def data_prep_undo_redo(request):
    """Handle undo and redo operations."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)
    
    dataset_id = request.POST.get("dataset_id", "").strip()
    action = request.POST.get("action", "").strip()
    
    try:
        dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
    except InvestorDatasetImport.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Dataset not found"}, status=404)
    
    prep_history = DataPrepHistory(dataset.prep_history or [])
    
    if action == "undo":
        if not prep_history.can_undo():
            return JsonResponse({"ok": False, "error": "Cannot undo"}, status=400)
        prep_history.undo()
    elif action == "redo":
        if not prep_history.can_redo():
            return JsonResponse({"ok": False, "error": "Cannot redo"}, status=400)
        prep_history.redo()
    else:
        return JsonResponse({"ok": False, "error": f"Unknown action: {action}"}, status=400)
    
    # Restore state from history
    current_state = prep_history.get_current_state()
    
    # Try to restore column_metadata and row_operations from state
    # This is simplified - a more robust approach would store full state in history
    
    dataset.prep_history = prep_history.serialize()
    dataset.save(update_fields=["prep_history"])
    
    # Generate updated preview
    all_rows = list(dataset.rows.all().values_list("payload", flat=True)[:10000])
    preview = LivePreviewGenerator.generate_preview(
        schema=dataset.schema,
        rows=all_rows,
        column_metadata=dataset.column_metadata or {},
        row_operations=dataset.row_operations or {},
    )
    
    return JsonResponse({
        "ok": True,
        "action": action,
        "can_undo": prep_history.can_undo(),
        "can_redo": prep_history.can_redo(),
        "preview": preview,
    })


@login_required
def data_prep_preview(request):
    """Get current data prep preview."""
    if request.method != "GET":
        return JsonResponse({"ok": False, "error": "GET required"}, status=405)
    
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return JsonResponse({"ok": False, "error": "Access Denied"}, status=403)
    
    dataset_id = request.GET.get("dataset_id", "").strip()
    limit = int(request.GET.get("limit", "50"))
    
    try:
        dataset = InvestorDatasetImport.objects.get(pk=dataset_id, investor=request.user)
    except InvestorDatasetImport.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Dataset not found"}, status=404)
    
    # Get all rows
    all_rows = list(dataset.rows.all().values_list("payload", flat=True)[:10000])
    
    # Generate preview
    preview = LivePreviewGenerator.generate_preview(
        schema=dataset.schema,
        rows=all_rows,
        column_metadata=dataset.column_metadata or {},
        row_operations=dataset.row_operations or {},
    )
    
    # Limit preview rows
    preview_rows = preview["rows"][:limit]
    
    return JsonResponse({
        "ok": True,
        "schema": preview["schema"],
        "rows": preview_rows,
        "row_count": preview["row_count"],
        "column_count": preview["column_count"],
        "original_row_count": preview["original_row_count"],
        "original_column_count": preview["original_column_count"],
        "rows_removed": preview["rows_removed"],
        "columns_removed": preview["columns_removed"],
    })


# -----------------------------------------------------------------------
# Admin Dashboard
# -----------------------------------------------------------------------
def _require_admin(request):
    """Return None if the user is a valid admin, otherwise an HttpResponseForbidden."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_superuser:
        return None
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return HttpResponseForbidden("Access Denied")
    return None


def _require_partner(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_superuser:
        return None
    if not hasattr(request.user, 'profile') or request.user.profile.role not in ('investor', 'analyst'):
        return HttpResponseForbidden("Access Denied")
    return None


def _build_otp_code():
    return f"{secrets.randbelow(1000000):06d}"


def _send_deletion_otp_email(admin_user, farmer, otp_code):
    if not admin_user.email:
        return False, "Admin account has no email configured."

    sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    try:
        send_mail(
            subject="1847 Ventures Farmer Deletion OTP",
            message=(
                f"Hello {admin_user.get_full_name() or admin_user.username},\n\n"
                f"OTP for deleting farmer account '{farmer.username}' is:\n"
                f"{otp_code}\n\n"
                "This OTP expires in 10 minutes.\n"
                "If you did not request this action, contact support immediately."
            ),
            from_email=sender_email,
            recipient_list=[admin_user.email],
            fail_silently=False,
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _open_deletion_request_for_admin(farmer, admin_user):
    return FarmerDeletionRequest.objects.filter(
        farmer=farmer,
        requested_by=admin_user,
        status__in=["otp_pending", "pending_partner_approval"],
    ).order_by("-created_at").first()


@login_required
def admin_dashboard(request):
    denied = _require_admin(request)
    if denied:
        return denied
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied

    admin_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    pending_farmers = Farmer.objects.filter(
        profile__role='farmer', profile__is_approved=False, is_active=True
    ).order_by('-registration_date')

    notifications = AdminNotification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]

    pending_activity_approvals = FarmActivity.objects.filter(
        verification_status="verified",
        admin_approval_status="pending",
    ).select_related("farmer", "verified_by").order_by("-verified_at", "-created_at")

    unread_count = AdminNotification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    show_users = request.GET.get("view_users") == "1"
    pending_reset_request_user_ids = list(
        PasswordResetRequest.objects.filter(status="pending").values_list("user_id", flat=True)
    )
    users_by_category = {
        "admin": Farmer.objects.filter(profile__role="admin").order_by("username"),
        "field_agent": Farmer.objects.filter(profile__role="field_agent").order_by("username"),
        "investor": Farmer.objects.filter(profile__role="investor").order_by("username"),
        "farmer": Farmer.objects.filter(profile__role="farmer").order_by("username"),
    }

    stats = {
        'total_farmers': Farmer.objects.filter(profile__role='farmer').count(),
        'pending_approvals': pending_farmers.count(),
        'pending_activity_approvals': pending_activity_approvals.count(),
        'total_agents': Farmer.objects.filter(profile__role='field_agent').count(),
        'total_partners': Farmer.objects.filter(profile__role='investor').count(),
        'total_admins': Farmer.objects.filter(profile__role='admin').count(),
        'total_users': Farmer.objects.count(),
    }

    unread_notifications_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    return render(request, "Farmers/admin_dashboard.html", {
        "admin_profile": admin_profile,
        "pending_farmers": pending_farmers,
        "notifications": notifications,
        "pending_activity_approvals": pending_activity_approvals,
        "unread_count": unread_count,
        "unread_messages_count": Message.objects.filter(receiver=request.user, is_read=False).count(),
        "unread_notifications_count": unread_notifications_count,
        "show_users": show_users,
        "pending_reset_request_user_ids": pending_reset_request_user_ids,
        "users_by_category": users_by_category,
        "stats": stats,
    })


@login_required
def approve_farmer_activity(request, activity_id):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    activity = get_object_or_404(
        FarmActivity,
        pk=activity_id,
        verification_status="verified",
    )

    activity.admin_approval_status = "approved"
    activity.admin_reviewed_by = request.user
    activity.admin_reviewed_at = timezone.now()
    activity.admin_review_notes = request.POST.get("admin_note", "").strip()
    activity.save(update_fields=[
        "admin_approval_status",
        "admin_reviewed_by",
        "admin_reviewed_at",
        "admin_review_notes",
        "updated_at",
    ])

    Message.objects.create(
        sender=request.user,
        receiver=activity.farmer,
        content=(
            f"Your activity update ({activity.get_activity_type_display()} on {activity.date}) "
            "has been approved by admin."
        ),
    )
    messages.success(request, f"Activity for {activity.farmer.username} approved.")
    return redirect("admin_dashboard")


@login_required
def reject_farmer_activity_approval(request, activity_id):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    activity = get_object_or_404(
        FarmActivity,
        pk=activity_id,
        verification_status="verified",
    )

    review_note = request.POST.get("admin_note", "").strip() or "Admin review requested updates."
    activity.admin_approval_status = "rejected"
    activity.admin_reviewed_by = request.user
    activity.admin_reviewed_at = timezone.now()
    activity.admin_review_notes = review_note
    activity.save(update_fields=[
        "admin_approval_status",
        "admin_reviewed_by",
        "admin_reviewed_at",
        "admin_review_notes",
        "updated_at",
    ])

    if activity.verified_by:
        Message.objects.create(
            sender=request.user,
            receiver=activity.verified_by,
            content=(
                f"Admin rejected verified activity for farmer {activity.farmer.username} "
                f"({activity.get_activity_type_display()}). Note: {review_note}"
            ),
        )

    Message.objects.create(
        sender=request.user,
        receiver=activity.farmer,
        content=(
            f"Your activity update ({activity.get_activity_type_display()} on {activity.date}) "
            f"was not approved. Note: {review_note}"
        ),
    )
    messages.warning(request, f"Activity for {activity.farmer.username} was rejected.")
    return redirect("admin_dashboard")


@login_required
def contact_submissions_admin(request):
    denied = _require_admin(request)
    if denied:
        return denied
    denied = _enforce_superuser_dashboard_gate(request)
    if denied:
        return denied

    submissions = ContactSubmission.objects.all()
    paginator = Paginator(submissions, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "Farmers/contact_submissions_admin.html", {
        "page_obj": page_obj,
        "submissions": page_obj.object_list,
        "unread_messages_count": Message.objects.filter(receiver=request.user, is_read=False).count(),
        "unread_notifications_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
    })


def request_password_reset_from_admin(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]

            user = Farmer.objects.filter(username__iexact=username, email__iexact=email, is_active=True).first()
            if not user:
                messages.error(request, "No active account matches that username and email.")
                return render(request, "Farmers/request_password_reset_from_admin.html", {"form": form})

            pending_request, created = PasswordResetRequest.objects.get_or_create(
                user=user,
                status="pending",
                defaults={
                    "requested_by_username": username,
                    "requested_by_email": email,
                },
            )

            if created:
                admin_users = Farmer.objects.filter(profile__role="admin", is_active=True)
                notification_message = (
                    f"Password reset requested by '{user.username}' ({user.email}). "
                    "Please generate and share a reset link from the admin dashboard."
                )
                AdminNotification.objects.bulk_create([
                    AdminNotification(
                        recipient=admin_user,
                        notification_type="info",
                        message=notification_message,
                        related_farmer=user,
                    )
                    for admin_user in admin_users
                ])
                messages.success(
                    request,
                    "Your request has been sent to the admin. You will receive a reset link after approval."
                )
            else:
                messages.info(request, "A reset request is already pending with the admin.")

            return redirect("login")
    else:
        form = PasswordResetRequestForm()

    return render(request, "Farmers/request_password_reset_from_admin.html", {"form": form})


@login_required
def upload_investor_profile_photo(request):
    """Allow investors and analysts to upload their profile photo"""
    if not _user_has_role(request.user, {"investor", "analyst"}):
        return HttpResponseForbidden("Access Denied")

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    photo = request.FILES.get("profile_photo")
    if not photo:
        messages.error(request, "Please choose an image file first.")
        return redirect("partner_dashboard")

    investor_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    investor_profile.profile_photo = _prepare_profile_photo(photo, request.POST)
    investor_profile.save(update_fields=["profile_photo"])
    messages.success(request, "Profile picture updated successfully.")
    return redirect(request.POST.get("next", "partner_dashboard"))


@login_required
def upload_admin_profile_photo(request):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    photo = request.FILES.get("profile_photo")
    if not photo:
        messages.error(request, "Please choose an image file first.")
        return redirect("admin_dashboard")

    admin_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    admin_profile.profile_photo = _prepare_profile_photo(photo, request.POST)
    admin_profile.save(update_fields=["profile_photo"])
    messages.success(request, "Profile picture updated successfully.")
    return redirect("admin_dashboard")


@login_required
def generate_password_reset_link(request, user_id):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    target_user = get_object_or_404(Farmer, pk=user_id, is_active=True)

    pending_request = PasswordResetRequest.objects.filter(
        user=target_user,
        status="pending",
    ).order_by("-created_at").first()

    if not pending_request:
        messages.error(request, f"No pending reset request for '{target_user.username}'.")
        return redirect("admin_dashboard")

    if not target_user.email:
        messages.error(request, f"User '{target_user.username}' has no email address.")
        return redirect("admin_dashboard")

    uidb64 = urlsafe_base64_encode(force_bytes(target_user.pk))
    token = default_token_generator.make_token(target_user)
    reset_path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    reset_link = request.build_absolute_uri(reset_path)

    sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    email_sent = True
    email_error = ""
    try:
        send_mail(
            subject="Your 1847 Ventures Password Reset Link",
            message=(
                f"Hello {target_user.get_full_name() or target_user.username},\n\n"
                "A password reset was requested for your 1847 Ventures account.\n"
                "Use the secure link below to set a new password:\n\n"
                f"{reset_link}\n\n"
                "If you did not request this reset, please contact an administrator immediately."
            ),
            from_email=sender_email,
            recipient_list=[target_user.email],
            fail_silently=False,
        )
    except Exception as exc:
        email_sent = False
        email_error = str(exc)

    if email_sent:
        pending_request.status = "completed"
        pending_request.processed_by = request.user
        pending_request.processed_at = timezone.now()
        pending_request.save(update_fields=["status", "processed_by", "processed_at"])
        messages.success(
            request,
            f"Password reset link sent to '{target_user.email}' for user '{target_user.username}'."
        )
    else:
        messages.error(
            request,
            (
                f"Could not send password reset email to '{target_user.email}'. "
                f"Error: {email_error or 'unknown email backend error'}. "
                "Request is still pending. Share this link manually if needed: "
                f"{reset_link}"
            )
        )

    return redirect("admin_dashboard")


@login_required
def create_user(request):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            role = form.cleaned_data["role"]
            first_name = form.cleaned_data.get("first_name", "")
            last_name = form.cleaned_data.get("last_name", "")

            new_user = Farmer(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            temporary_password = f"1847@{secrets.randbelow(1000000):06d}"
            new_user.set_password(temporary_password)
            new_user.save()

            profile = new_user.profile
            profile.role = role
            profile.is_approved = role != "farmer"
            profile.must_change_password = True
            profile.save()

            sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
            email_sent = True
            email_error = ""
            try:
                send_mail(
                    subject="Your 1847 Ventures Temporary Password",
                    message=(
                        f"Hello {first_name or username},\n\n"
                        "Your account has been created.\n"
                        f"Temporary password: {temporary_password}\n\n"
                        "Please sign in and change your password immediately."
                    ),
                    from_email=sender_email,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as exc:
                email_sent = False
                email_error = str(exc)

            role_label = dict(CreateUserForm.ROLE_CHOICES).get(role, role)
            if profile.is_approved:
                messages.success(
                    request,
                    f"{role_label} account '{username}' created and auto-approved successfully."
                )
            else:
                messages.success(
                    request,
                    f"{role_label} account '{username}' created successfully and is pending approval."
                )

            if email_sent:
                messages.info(
                    request,
                    f"Temporary password email sent to {email}. User must change password on first login."
                )
            else:
                messages.warning(
                    request,
                    (
                        f"Could not send temporary password email to {email}. "
                        f"Error: {email_error or 'unknown email backend error'}. "
                        f"Temporary password: {temporary_password}"
                    )
                )
            return redirect("admin_dashboard")
    else:
        role_prefill = request.GET.get("role", "field_agent")
        form = CreateUserForm(initial={"role": role_prefill})

    return render(request, "Farmers/create_user.html", {"form": form})


@login_required
def assign_farmer_request(request):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method == "POST":
        form = FarmerRegistrationRequestForm(request.POST)
        if form.is_valid():
            FarmerRegistrationRequest.objects.create(
                created_by=request.user,
                assigned_agent=form.cleaned_data["assigned_agent"],
                farmer_name=form.cleaned_data["farmer_name"],
                farmer_email=form.cleaned_data.get("farmer_email", ""),
                farmer_phone=form.cleaned_data.get("farmer_phone", ""),
                notes=form.cleaned_data.get("notes", ""),
            )
            messages.success(
                request,
                f"Farmer registration request assigned to "
                f"'{form.cleaned_data['assigned_agent'].username}' successfully."
            )
            return redirect("admin_dashboard")
    else:
        form = FarmerRegistrationRequestForm()

    return render(request, "Farmers/assign_farmer_request.html", {"form": form})


@login_required
def review_farmer(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')
    deletion_request = _open_deletion_request_for_admin(farmer, request.user)
    action = (request.GET.get("action") or "").strip().lower()
    delete_stage = ""

    # Keep deletion panel visible for actionable/request states, even without explicit query param.
    if farmer.profile.is_approved and deletion_request:
        if deletion_request.status in {"otp_pending", "pending_partner_approval", "rejected"}:
            action = "delete_request"
        if deletion_request.status == "otp_pending":
            delete_stage = "otp"

    return render(request, "Farmers/review_farmer.html", {
        "farmer": farmer,
        "sheet1": getattr(farmer, "assessment_sheet1", None),
        "sheet2": getattr(farmer, "assessment_sheet2", None),
        "sheet3": getattr(farmer, "assessment_sheet3", None),
        "activity_log": _build_farmer_activity_log(farmer),
        "deletion_request": deletion_request,
        "action": action,
        "delete_stage": delete_stage,
    })


@login_required
def initiate_farmer_deletion_request(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')
    if not farmer.profile.is_approved:
        messages.error(request, "Deletion workflow is available only for farmers already active in the system.")
        return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")

    password = request.POST.get("admin_password", "")
    if not request.user.check_password(password):
        messages.error(request, "Password confirmation failed. Deletion request was not started.")
        return render(request, "Farmers/review_farmer.html", {
            "farmer": farmer,
            "sheet1": getattr(farmer, "assessment_sheet1", None),
            "sheet2": getattr(farmer, "assessment_sheet2", None),
            "sheet3": getattr(farmer, "assessment_sheet3", None),
            "activity_log": _build_farmer_activity_log(farmer),
            "deletion_request": _open_deletion_request_for_admin(farmer, request.user),
            "action": "delete_request",
            "delete_stage": "password",
        })

    active_request = _open_deletion_request_for_admin(farmer, request.user)
    if active_request and active_request.status == "pending_partner_approval":
        messages.info(request, "This farmer deletion is already awaiting partner approval.")
        return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")

    otp_code = _build_otp_code()
    otp_expires_at = timezone.now() + timezone.timedelta(minutes=10)

    if active_request:
        deletion_request = active_request
    else:
        deletion_request = FarmerDeletionRequest(farmer=farmer, requested_by=request.user)

    deletion_request.status = "otp_pending"
    deletion_request.otp_hash = make_password(otp_code)
    deletion_request.otp_expires_at = otp_expires_at
    deletion_request.otp_verified_at = None
    deletion_request.partner_reviewer = None
    deletion_request.rejection_reason = ""
    deletion_request.save()

    email_sent, email_error = _send_deletion_otp_email(request.user, farmer, otp_code)
    if not email_sent:
        messages.error(request, f"Could not send OTP email: {email_error or 'unknown email backend error'}")
        return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")

    messages.success(request, "OTP sent to your admin email. Enter it to submit deletion for partner approval.")
    return render(request, "Farmers/review_farmer.html", {
        "farmer": farmer,
        "sheet1": getattr(farmer, "assessment_sheet1", None),
        "sheet2": getattr(farmer, "assessment_sheet2", None),
        "sheet3": getattr(farmer, "assessment_sheet3", None),
        "activity_log": _build_farmer_activity_log(farmer),
        "deletion_request": deletion_request,
        "action": "delete_request",
        "delete_stage": "otp",
    })


@login_required
def verify_farmer_deletion_otp(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')
    deletion_request = _open_deletion_request_for_admin(farmer, request.user)
    if not deletion_request or deletion_request.status != "otp_pending":
        messages.error(request, "No OTP-pending deletion request was found for this farmer.")
        return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")

    otp = request.POST.get("otp_code", "").strip()
    if not otp:
        messages.error(request, "Enter the OTP sent to your email.")
        return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")

    if not deletion_request.otp_expires_at or deletion_request.otp_expires_at < timezone.now():
        messages.error(request, "OTP expired. Start deletion again to receive a new OTP.")
        return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")

    if not check_password(otp, deletion_request.otp_hash):
        messages.error(request, "Invalid OTP. Please try again.")
        return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")

    deletion_request.status = "pending_partner_approval"
    deletion_request.otp_hash = ""
    deletion_request.otp_verified_at = timezone.now()
    deletion_request.save(update_fields=["status", "otp_hash", "otp_verified_at", "updated_at"])

    partner_users = Farmer.objects.filter(
        profile__role__in=["investor", "analyst"],
        is_active=True,
    )
    for partner_user in partner_users:
        Message.objects.create(
            sender=request.user,
            receiver=partner_user,
            content=(
                f"Farmer deletion approval needed for '{farmer.username}' ({farmer.email}). "
                "Please review in Partner Dashboard > Admin & Data Governance."
            ),
        )

    messages.success(request, "Deletion request submitted to partner for final approval.")
    return redirect(f"{reverse('review_farmer', kwargs={'farmer_id': farmer.pk})}?action=delete_request")


@login_required
def partner_approve_farmer_deletion(request, deletion_request_id):
    denied = _require_partner(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    deletion_request = get_object_or_404(
        FarmerDeletionRequest,
        pk=deletion_request_id,
        status="pending_partner_approval",
    )
    farmer = deletion_request.farmer
    admin_user = deletion_request.requested_by
    field_agent = getattr(getattr(farmer, "profile", None), "created_by_agent", None)
    farmer_username = farmer.username

    with transaction.atomic():
        if field_agent and field_agent.is_active:
            Message.objects.create(
                sender=request.user,
                receiver=field_agent,
                content=(
                    f"Farmer account '{farmer_username}' was permanently deleted after partner approval."
                ),
            )

        AdminNotification.objects.filter(related_farmer=farmer).delete()
        FarmerDeletionRequest.objects.filter(farmer=farmer).delete()
        farmer.delete()

    if admin_user and admin_user.is_active:
        Message.objects.create(
            sender=request.user,
            receiver=admin_user,
            content=f"Deletion approved and completed for farmer '{farmer_username}'.",
        )

    messages.success(request, "Farmer deletion approved and completed permanently.")
    return redirect("partner_dashboard")


@login_required
def partner_reject_farmer_deletion(request, deletion_request_id):
    denied = _require_partner(request)
    if denied:
        return denied

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method")

    deletion_request = get_object_or_404(
        FarmerDeletionRequest,
        pk=deletion_request_id,
        status="pending_partner_approval",
    )
    reason = request.POST.get("reason", "").strip() or "No reason provided."
    deletion_request.status = "rejected"
    deletion_request.partner_reviewer = request.user
    deletion_request.rejection_reason = reason
    deletion_request.save(update_fields=["status", "partner_reviewer", "rejection_reason", "updated_at"])

    if deletion_request.requested_by and deletion_request.requested_by.is_active:
        Message.objects.create(
            sender=request.user,
            receiver=deletion_request.requested_by,
            content=(
                f"Partner rejected deletion request for farmer '{deletion_request.farmer.username}'. "
                f"Reason: {reason}"
            ),
        )

    messages.info(request, "Farmer deletion request rejected.")
    return redirect("partner_dashboard")


def _send_farmer_password_setup_email(request, farmer):
    if not farmer.email:
        return False, "Farmer has no email address.", "", ""

    uidb64 = urlsafe_base64_encode(force_bytes(farmer.pk))
    token = default_token_generator.make_token(farmer)
    reset_path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    reset_link = request.build_absolute_uri(reset_path)

    temporary_password = f"1847F@{secrets.randbelow(1000000):06d}"
    farmer.set_password(temporary_password)
    farmer.save(update_fields=["password"])

    sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    try:
        send_mail(
            subject="Your 1847 Ventures Account Has Been Approved",
            message=(
                f"Hello {farmer.get_full_name() or farmer.username},\n\n"
                "Your farmer account has been approved by the admin.\n"
                "You can access your account using either option below:\n\n"
                "Option 1 - Set your own password with this secure link:\n"
                f"{reset_link}\n\n"
                "Option 2 - Log in directly with your one-time credentials:\n"
                f"Username: {farmer.username}\n"
                f"One-time password: {temporary_password}\n\n"
                "After login, you will be prompted to change your password.\n\n"
                "If you did not expect this email, please contact support."
            ),
            from_email=sender_email,
            recipient_list=[farmer.email],
            fail_silently=False,
        )
        return True, "", reset_link, temporary_password
    except Exception as exc:
        return False, str(exc), reset_link, temporary_password


@login_required
def approve_farmer(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')
    profile = farmer.profile

    email_sent, email_error, reset_link, temporary_password = _send_farmer_password_setup_email(request, farmer)
    if not email_sent:
        farmer.set_unusable_password()
        farmer.save(update_fields=["password"])
        profile.is_approved = False
        profile.must_change_password = False
        profile.save(update_fields=["is_approved", "must_change_password"])
        messages.error(
            request,
            (
                f"Farmer '{farmer.username}' was not approved because onboarding email failed. "
                f"Error: {email_error or 'unknown email backend error'}. "
                f"Password setup link: {reset_link or 'not generated'}"
            ),
        )
        return redirect("admin_dashboard")

    profile.is_approved = True
    profile.must_change_password = True
    profile.save(update_fields=["is_approved", "must_change_password"])

    AdminNotification.objects.filter(
        related_farmer=farmer, is_read=False
    ).update(is_read=True)

    messages.success(
        request,
        f"Farmer '{farmer.username}' has been approved and onboarding email was sent to {farmer.email}."
    )
    messages.info(
        request,
        f"One-time login password generated for '{farmer.username}': {temporary_password}"
    )
    return redirect("admin_dashboard")


@login_required
def reject_farmer(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')

    if request.method == "POST":
        reason = request.POST.get("reason", "No reason provided.")
        agent = farmer.profile.created_by_agent
        if agent:
            Message.objects.create(
                sender=request.user,
                receiver=agent,
                content=(
                    f"Farmer registration for '{farmer.username}' ({farmer.email}) "
                    f"has been rejected.\nReason: {reason}"
                ),
            )

        AdminNotification.objects.filter(
            related_farmer=farmer, is_read=False
        ).update(is_read=True)

        farmer.is_active = False
        farmer.save()
        messages.success(request, f"Farmer '{farmer.username}' has been rejected.")
        return redirect("admin_dashboard")

    return render(request, "Farmers/review_farmer.html", {
        "farmer": farmer,
        "sheet1": getattr(farmer, "assessment_sheet1", None),
        "sheet2": getattr(farmer, "assessment_sheet2", None),
        "sheet3": getattr(farmer, "assessment_sheet3", None),
        "activity_log": _build_farmer_activity_log(farmer),
        "action": "reject",
    })


@login_required
def request_more_info(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')

    if request.method == "POST":
        info_request = request.POST.get("info_request", "").strip()
        if not info_request:
            messages.error(request, "Please describe what additional information is needed.")
            return render(request, "Farmers/review_farmer.html", {
                "farmer": farmer,
                "sheet1": getattr(farmer, "assessment_sheet1", None),
                "sheet2": getattr(farmer, "assessment_sheet2", None),
                "sheet3": getattr(farmer, "assessment_sheet3", None),
                "activity_log": _build_farmer_activity_log(farmer),
                "action": "request_info",
            })

        agent = farmer.profile.created_by_agent
        if agent:
            Message.objects.create(
                sender=request.user,
                receiver=agent,
                content=(
                    f"Additional information is needed for farmer '{farmer.username}' ({farmer.email}).\n\n"
                    f"Details: {info_request}"
                ),
            )
            messages.success(
                request,
                f"Information request sent to field agent '{agent.username}'."
            )
        else:
            messages.warning(
                request,
                "No field agent is linked to this farmer. Could not send request."
            )
        return redirect("admin_dashboard")

    return render(request, "Farmers/review_farmer.html", {
        "farmer": farmer,
        "sheet1": getattr(farmer, "assessment_sheet1", None),
        "sheet2": getattr(farmer, "assessment_sheet2", None),
        "sheet3": getattr(farmer, "assessment_sheet3", None),
        "activity_log": _build_farmer_activity_log(farmer),
        "action": "request_info",
    })


@login_required
def mark_notification_read(request, notification_id):
    denied = _require_admin(request)
    if denied:
        return denied

    notification = get_object_or_404(
        AdminNotification, pk=notification_id, recipient=request.user
    )
    notification.is_read = True
    notification.save()
    return redirect("admin_dashboard")


# =================================================
# THREE-SHEET FARM ASSESSMENT VIEWS
# See → Ask → Select (No Free Text, No Calculations)
# =================================================

@login_required
def farm_assessment_sheet1(request, farmer_id):
    """SHEET 1: Farmer Profile & Location"""
    
    # Only field agents can collect data
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'field_agent':
        return HttpResponseForbidden("Only field agents can access this page.")
    
    farmer = get_object_or_404(_field_agent_farmer_queryset(request.user), pk=farmer_id)
    
    # Get or create assessment
    assessment, created = FarmAssessmentSheet1.objects.get_or_create(farmer=farmer)
    
    if request.method == "POST":
        form = FarmAssessmentSheet1Form(request.POST, instance=assessment)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.collected_by = request.user
            assessment.save()
            messages.success(request, "✓ Sheet 1 saved. Proceed to Sheet 2: Farm Assessment")
            return redirect("farm_assessment_sheet2", farmer_id=farmer.pk)
    else:
        form = FarmAssessmentSheet1Form(instance=assessment)
    
    return render(request, "Farmers/assessment_sheet1.html", {
        "form": form,
        "farmer": farmer,
        "sheet_number": 1,
        "total_sheets": 3,
    })


@login_required
def farm_assessment_sheet2(request, farmer_id):
    """SHEET 2: Farm Assessment (Size, Trees, Activities)"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'field_agent':
        return HttpResponseForbidden("Only field agents can access this page.")
    
    farmer = get_object_or_404(_field_agent_farmer_queryset(request.user), pk=farmer_id)
    
    # Ensure Sheet 1 is complete before proceeding
    try:
        sheet1 = FarmAssessmentSheet1.objects.get(farmer=farmer)
    except FarmAssessmentSheet1.DoesNotExist:
        messages.warning(request, "Please complete Sheet 1 first.")
        return redirect("farm_assessment_sheet1", farmer_id=farmer.pk)
    
    assessment, created = FarmAssessmentSheet2.objects.get_or_create(farmer=farmer)
    
    if request.method == "POST":
        form = FarmAssessmentSheet2Form(request.POST, instance=assessment)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.collected_by = request.user
            assessment.save()
            messages.success(request, "✓ Sheet 2 saved. Proceed to Sheet 3: Verification")
            return redirect("farm_assessment_sheet3", farmer_id=farmer.pk)
    else:
        form = FarmAssessmentSheet2Form(instance=assessment)
    
    return render(request, "Farmers/assessment_sheet2.html", {
        "form": form,
        "farmer": farmer,
        "sheet_number": 2,
        "total_sheets": 3,
    })


@login_required
def farm_assessment_sheet3(request, farmer_id):
    """SHEET 3: Verification & Evidence (Photos, Voice Notes)"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'field_agent':
        return HttpResponseForbidden("Only field agents can access this page.")
    
    farmer = get_object_or_404(_field_agent_farmer_queryset(request.user), pk=farmer_id)
    
    # Ensure Sheet 2 is complete
    try:
        sheet2 = FarmAssessmentSheet2.objects.get(farmer=farmer)
    except FarmAssessmentSheet2.DoesNotExist:
        messages.warning(request, "Please complete Sheet 2 first.")
        return redirect("farm_assessment_sheet2", farmer_id=farmer.pk)
    
    assessment, created = FarmAssessmentSheet3.objects.get_or_create(farmer=farmer)
    
    if request.method == "POST":
        form = FarmAssessmentSheet3Form(request.POST, request.FILES, instance=assessment)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.collected_by = request.user
            
            # Validate completion
            if form.cleaned_data.get("photo_of_farmer") and form.cleaned_data.get("photo_of_farm"):
                assessment.photos_complete = True
            
            assessment.save()
            farmer_profile, _ = UserProfile.objects.get_or_create(user=farmer)
            if assessment.photo_of_farmer:
                farmer_profile.profile_photo = assessment.photo_of_farmer
                farmer_profile.save(update_fields=["profile_photo"])
            messages.success(
                request,
                "✅ Assessment Complete! All three sheets have been submitted successfully."
            )
            return redirect("agent_dashboard")
    else:
        form = FarmAssessmentSheet3Form(instance=assessment)
    
    return render(request, "Farmers/assessment_sheet3.html", {
        "form": form,
        "farmer": farmer,
        "sheet_number": 3,
        "total_sheets": 3,
    })



# ------------------------------------------------------------------------------
# Custom error handlers
# ------------------------------------------------------------------------------

def csrf_failure(request, reason=""):
    "Custom CSRF failure page - shown instead of Django's debug 403 page."
    return render(request, "Farmers/403.html", {"reason": reason}, status=403)


def page_not_found(request, exception=None):
    "Custom 404 page."
    return render(request, "Farmers/404.html", {}, status=404)
