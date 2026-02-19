from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied

class ApprovedUserBackend(ModelBackend):
    def user_can_authenticate(self, user):
        if not super().user_can_authenticate(user):
            return False

        # Superusers always allowed
        if user.is_superuser:
            return True

        # Block unapproved users
        if hasattr(user, "profile") and not user.profile.is_approved:
            raise PermissionDenied("Account pending admin approval.")

        return True
