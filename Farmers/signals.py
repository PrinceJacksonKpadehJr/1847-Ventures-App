from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.messages.api import MessageFailure

@receiver(user_logged_in)
def block_unapproved_users(sender, request, user, **kwargs):
    """Immediately sign out non-superusers pending approval."""
    if user.is_superuser:
        return

    if hasattr(user, "profile") and not user.profile.is_approved:
        logout(request)
        try:
            messages.error(
                request,
                "Your account is pending approval. Please wait for admin confirmation."
            )
        except MessageFailure:
            # Some auth flows (for example scripted force_login) may not have messages storage.
            pass
