import logging
import time

from django.conf import settings
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse


logger = logging.getLogger(__name__)


class _DBQueryCollector:
    def __init__(self):
        self.count = 0
        self.duration_ms = 0.0

    def __call__(self, execute, sql, params, many, context):
        started = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.count += 1
            self.duration_ms += (time.perf_counter() - started) * 1000


class RequestPerformanceMiddleware:
    """Opt-in request profiler for startup/perf diagnostics.

    Enable with PERF_MONITORING_ENABLED=true in environment or settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = bool(getattr(settings, "PERF_MONITORING_ENABLED", False))
        self.request_warn_ms = float(getattr(settings, "PERF_REQUEST_WARN_MS", 600.0))
        self.db_warn_ms = float(getattr(settings, "PERF_DB_WARN_MS", 250.0))

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)

        collector = _DBQueryCollector()
        started = time.perf_counter()
        with connection.execute_wrapper(collector):
            response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000

        prior_server_timing = response.get("Server-Timing")
        timing_value = f"app;dur={elapsed_ms:.1f}, db;dur={collector.duration_ms:.1f}"
        response["Server-Timing"] = (
            f"{prior_server_timing}, {timing_value}" if prior_server_timing else timing_value
        )
        response["X-DB-Query-Count"] = str(collector.count)

        if elapsed_ms >= self.request_warn_ms or collector.duration_ms >= self.db_warn_ms:
            logger.warning(
                "Slow request method=%s path=%s status=%s total_ms=%.1f db_ms=%.1f db_queries=%s",
                request.method,
                request.path,
                getattr(response, "status_code", "unknown"),
                elapsed_ms,
                collector.duration_ms,
                collector.count,
            )

        return response


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.is_superuser:
            profile = getattr(user, "profile", None)
            if profile and profile.must_change_password:
                allowed_paths = {
                    reverse("force_password_change"),
                    reverse("logout"),
                }
                if (
                    request.path not in allowed_paths
                    and not request.path.startswith("/static/")
                    and not request.path.startswith("/media/")
                ):
                    return redirect("force_password_change")

        return self.get_response(request)
