from django.contrib import admin
from django.contrib import messages as django_messages
from .models import (
    Farmer,
    UserProfile,
    Farm,
    Crop,
    Harvest,
    Investment,
    FarmActivity,
    Announcement,
    Message,
)
from .utils import send_password_setup_email


# ===== Admin action =====
@admin.action(description="Approve selected farmers and send password-setup email")
def approve_farmers(modeladmin, request, queryset):
    """Approve selected UserProfiles and e-mail each farmer a password-setup link."""
    approved_count = 0
    for profile in queryset.filter(is_approved=False, role="farmer"):
        profile.is_approved = True
        profile.save()
        # Email is sent via post_save signal -- see signals.py on_profile_approved
        approved_count += 1

    if approved_count:
        django_messages.success(
            request,
            f"{approved_count} farmer(s) approved. Password-setup email(s) sent.",
        )
    else:
        django_messages.warning(request, "No pending farmer profiles were found in the selection.")


# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('username', 'farmer_id', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'farmer_id', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

# ===== Register User Profile =======
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "user_email", "is_approved")
    list_filter = ("is_approved", "role")
    search_fields = ("user__username", "user__email")
    actions = [approve_farmers]

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

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
