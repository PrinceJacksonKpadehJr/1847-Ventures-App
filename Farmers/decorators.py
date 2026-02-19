from rest_framework.response import Response
from rest_framework import status
from functools import wraps

def approved_user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Superusers bypass approval
        if user.is_superuser:
            return view_func(self, request, *args, **kwargs)

        if hasattr(user, "profile") and not user.profile.is_approved:
            return Response(
                {"detail": "Your account is pending admin approval."},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return _wrapped_view
