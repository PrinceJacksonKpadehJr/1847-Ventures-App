from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.contrib import messages as django_messages


@receiver(user_logged_in)
def block_unapproved_users(sender, request, user, **kwargs):
    """Log-in gate: non-superusers must be approved before accessing the site."""
    if user.is_superuser:
        return

    if hasattr(user, "profile") and not user.profile.is_approved:
        from django.contrib.auth import logout
        logout(request)
        django_messages.error(
            request,
            "Your account is pending approval. Please wait for admin confirmation.",
        )


# Track the previous is_approved value before a UserProfile save so we can
# detect the False -> True transition in post_save.
@receiver(pre_save, sender="Farmers.UserProfile")
def capture_previous_approval(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._was_approved = sender.objects.get(pk=instance.pk).is_approved
        except sender.DoesNotExist:
            instance._was_approved = False
    else:
        instance._was_approved = False


@receiver(post_save, sender="Farmers.UserProfile")
def notify_farmer_on_approval(sender, instance, created, **kwargs):
    """
    When is_approved flips from False -> True (outside the admin), generate a
    password-setup token and deliver it via an in-app Message (and email if
    available).  When the change originates from the admin UI the admin's
    save_model already handles the notification, so we skip here to avoid
    sending the farmer a duplicate message.
    """
    if getattr(instance, "_approval_handled_by_admin", False):
        return  # Admin handled it; avoid duplicate notification

    was_approved = getattr(instance, "_was_approved", False)
    if not created and not was_approved and instance.is_approved:
        _send_password_setup_notification(instance)


def _send_password_setup_notification(profile):
    """Create an in-app Message containing the password-setup link, and
    optionally send an email if the farmer has an address on file."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.urls import reverse
    from .models import Message, Farmer

    farmer = profile.user

    # Try to locate a superuser to act as the 'sender' of the in-app message.
    admin_user = Farmer.objects.filter(is_superuser=True).first()
    if admin_user is None:
        return  # No admin exists yet; skip notification

    uid = urlsafe_base64_encode(force_bytes(farmer.pk))
    token = default_token_generator.make_token(farmer)
    setup_path = reverse(
        "farmer_set_password", kwargs={"uidb64": uid, "token": token}
    )
    # Store the relative path; the farmer sees the full link after domain is known.
    setup_url = setup_path

    message_body = (
        "Your 1847 Ventures account has been approved!\n\n"
        "Please set your password by visiting this link:\n"
        f"{setup_url}\n\n"
        "(If you are reading this as an in-app message, copy the path above "
        "and append it to the site domain in your browser.)\n\n"
        "Once you set your password you can log in normally."
    )

    Message.objects.create(
        sender=admin_user,
        receiver=farmer,
        content=message_body,
    )

    # Send email if the farmer has an address and email is configured.
    if farmer.email:
        from django.core.mail import send_mail
        from django.conf import settings as django_settings

        try:
            send_mail(
                subject="Your 1847 Ventures account is approved - set your password",
                message=(
                    f"Hello {farmer.username},\n\n"
                    "Your 1847 Ventures account has been approved.\n\n"
                    f"Set your password here: {setup_url}\n\n"
                    "Best regards,\n1847 Ventures Team"
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[farmer.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Email is best-effort; in-app message is the primary channel.
