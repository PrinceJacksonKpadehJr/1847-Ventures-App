from django.contrib import admin
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.urls import reverse
from .models import UserProfile
from .models import (
    Farmer,
    UserProfile,
    Farm,
    Crop,
    Harvest,
    Investment,
    FarmActivity,
    Announcement,
    Message
)


def _send_password_setup_email(request, farmer):
    """Send a password-setup email to a newly approved farmer."""
    uid = urlsafe_base64_encode(force_bytes(farmer.pk))
    token = default_token_generator.make_token(farmer)
    reset_url = request.build_absolute_uri(
        reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    )
    subject = "1847 Ventures — Your account has been approved"
    message = (
        f"Hello {farmer.username},\n\n"
        f"Your 1847 Ventures account has been approved by an administrator.\n\n"
        f"Please click the link below to set your password and log in:\n"
        f"{reset_url}\n\n"
        f"This link will expire after 72 hours.\n\n"
        f"— The 1847 Ventures Team"
    )
    send_mail(
        subject,
        message,
        django_settings.DEFAULT_FROM_EMAIL,
        [farmer.email],
        fail_silently=True,
    )


@admin.action(description="Approve selected farmers and send password setup email")
def approve_farmers(modeladmin, request, queryset):
    approved_count = 0
    skipped_no_email = 0
    for profile in queryset.filter(is_approved=False).select_related("user"):
        farmer = profile.user
        profile.is_approved = True
        profile.save()
        if farmer.email:
            _send_password_setup_email(request, farmer)
        else:
            skipped_no_email += 1
        approved_count += 1

    if approved_count:
        modeladmin.message_user(
            request,
            f"{approved_count} farmer(s) approved. Password setup emails sent where email was available."
        )
    if skipped_no_email:
        modeladmin.message_user(
            request,
            f"{skipped_no_email} farmer(s) approved without email — no setup email was sent.",
            level="warning",
        )


# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'farmer_id', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'farmer_id', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

# ===== Register User Profile =======
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_approved")
    list_filter = ("is_approved", "role")
    search_fields = ("user__username", "user__email")
    actions = [approve_farmers]

# ===== Farm Admin =====
@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'size_in_hectares', 'created_at')
    search_fields = ('name', 'owner__username', 'location')

# ===== Crop Admin =====
@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ('name', 'farm', 'planting_date', 'harvest_date', 'expected_yield_kg')
    search_fields = ('name', 'farm__name')

# ===== Harvest Admin =====
@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):
    list_display = ('farm', 'date_of_harvest', 'tons_produced', 'quality_grade')
    search_fields = ('farm__name',)

# ===== Investment Admin =====
@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('investor', 'farm', 'amount', 'expected_return_percentage', 'invested_at')
    search_fields = ('investor__username', 'farm__name')

# ===== FarmActivity Admin =====
@admin.register(FarmActivity)
class FarmActivityAdmin(admin.ModelAdmin):
    list_display = ('farmer', 'activity_type', 'date', 'quantity')
    search_fields = ('farmer__username',)

# ===== Announcement Admin =====
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'is_active')
    search_fields = ('title', 'created_by__username')

# ===== Message Admin =====
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'created_at', 'is_read')
    search_fields = ('sender__username', 'receiver__username')
