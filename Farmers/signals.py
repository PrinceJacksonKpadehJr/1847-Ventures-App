from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(pre_save, sender=UserProfile)
def cache_approval_status(sender, instance, **kwargs):
    """Cache the previous is_approved value so the post_save signal can detect transitions."""
    if instance.pk:
        try:
            instance._was_approved = UserProfile.objects.get(pk=instance.pk).is_approved
        except UserProfile.DoesNotExist:
            instance._was_approved = False
    else:
        instance._was_approved = False


@receiver(post_save, sender=UserProfile)
def on_profile_approved(sender, instance, created, **kwargs):
    """When a farmer profile transitions to is_approved=True, send the password-setup email."""
    if created:
        return

    was_approved = getattr(instance, "_was_approved", False)
    if not was_approved and instance.is_approved and instance.role == "farmer":
        user = instance.user
        if not user.has_usable_password():
            from .utils import send_password_setup_email
            send_password_setup_email(user)
