from django.shortcuts import redirect
from django.urls import reverse


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
