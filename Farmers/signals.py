from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib import messages
from django.contrib.auth import logout

@receiver(user_logged_in)
def block_unapproved_users(sender, request, user, **kwargs):
    # Superusers bypass approval
    if user.is_superuser:
        return

    if hasattr(user, "profile") and not user.profile.is_approved:
        logout(request)
        messages.error(
            request,
            "Your account is pending approval. Please wait for admin confirmation."
        )

@receiver(user_logged_in)
def block_unapproved_users(sender, request, user, **kwargs):
    if user.is_superuser:
        return

    if hasattr(user, "profile") and not user.profile.is_approved:
        logout(request)
        messages.error(request, "Your account is pending approval. Please wait for admin confirmation.")