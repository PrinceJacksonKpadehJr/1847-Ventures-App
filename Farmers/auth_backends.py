from django.contrib.auth.backends import ModelBackend


class ApprovedUserBackend(ModelBackend):
    def user_can_authenticate(self, user):
        if not super().user_can_authenticate(user):
            return False

        # Superusers always allowed
        if user.is_superuser:
            return True

        # Block unapproved users — return False so the login form shows a
        # generic "invalid credentials" error; the view adds a specific message.
        if hasattr(user, "profile") and not user.profile.is_approved:
            return False

        return True
