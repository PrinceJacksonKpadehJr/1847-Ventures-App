from django.contrib import admin
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
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


def _get_farmer_email(profile):
    """Return email from UserProfile, falling back to Farmer.email."""
    return profile.email or profile.user.email or None


@admin.action(description="Approve selected users and send password setup email")
def approve_farmers(modeladmin, request, queryset):
    approved_count = 0
    for profile in queryset:
        farmer = profile.user
        email = _get_farmer_email(profile)

        if not email:
            modeladmin.message_user(
                request,
                f"Skipped {farmer.username}: no email address on file.",
                level="warning",
            )
            continue

        # Sync email to Farmer model so Django built-ins work
        if not farmer.email:
            farmer.email = email
            farmer.save(update_fields=["email"])

        profile.is_approved = True
        profile.save(update_fields=["is_approved"])

        token = default_token_generator.make_token(farmer)
        uid = urlsafe_base64_encode(force_bytes(farmer.pk))
        reset_url = request.build_absolute_uri(
            f"/reset/{uid}/{token}/"
        )

        send_mail(
            subject="Set your 1847 Ventures password",
            message=(
                f"Hello {farmer.username},\n\n"
                "Your account has been approved by an administrator.\n\n"
                "Please set your password by visiting the link below:\n\n"
                f"{reset_url}\n\n"
                "This link is valid for 3 days. If you did not expect this "
                "email, please ignore it."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        approved_count += 1

    if approved_count:
        modeladmin.message_user(
            request,
            f"Successfully approved {approved_count} account(s) and sent password setup emails."
        )


# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('username', 'farmer_id', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'farmer_id', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

# ===== Register User Profile =======
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "role", "is_approved")
    list_filter = ("is_approved", "role")
    search_fields = ("user__username", "user__email", "email")
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




