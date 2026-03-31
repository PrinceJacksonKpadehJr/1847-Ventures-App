from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings


def send_password_setup_email(user, request=None):
    """
    Send a password-setup email to a newly approved farmer.
    Uses Django's default password-reset token generator so the link
    is secure and time-limited.
    """
    if not user.email:
        return

    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    if request is not None:
        domain = request.get_host()
        protocol = "https" if request.is_secure() else "http"
    else:
        domain = getattr(settings, "SITE_DOMAIN", "localhost:8000")
        protocol = "http"

    reset_url = f"{protocol}://{domain}/password-reset-confirm/{uid}/{token}/"

    subject = "Set up your 1847 Ventures password"
    message = (
        f"Hello {user.username},\n\n"
        "Your 1847 Ventures account has been approved by the administrator.\n\n"
        "Please click the link below to create your password and activate your account:\n"
        f"{reset_url}\n\n"
        "This link is valid for a limited time. If you did not request this, "
        "please ignore this email.\n\n"
        "Best regards,\n1847 Ventures Team"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )
