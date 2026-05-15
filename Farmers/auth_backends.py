from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class ApprovedUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Accept either username or email in the login form input.
        user_model = get_user_model()
        login_value = username or kwargs.get(user_model.USERNAME_FIELD) or kwargs.get("email")
        if login_value is None or password is None:
            return None

        try:
            user = user_model._default_manager.get(
                Q(username__iexact=login_value) | Q(email__iexact=login_value)
            )
        except user_model.DoesNotExist:
            # Keep timing behavior close to valid-user flow.
            user_model().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        # Keep backend focused on credential validity and active status.
        # Role/approval checks are handled in CustomLoginView.form_valid.
        return super().user_can_authenticate(user)
