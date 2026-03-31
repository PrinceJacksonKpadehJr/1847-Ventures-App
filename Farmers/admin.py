from django.contrib import admin
from .models import UserProfile
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

# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('username', 'farmer_id', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'farmer_id', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')


# ===== Admin action to approve selected users =====
@admin.action(description="Approve selected users")
def approve_users(modeladmin, request, queryset):
    updated = queryset.update(is_approved=True)
    modeladmin.message_user(request, f"{updated} user(s) approved successfully.")


# ===== Register User Profile =======
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_approved", "approval_status")
    list_filter = ("is_approved", "role")
    search_fields = ("user__username", "user__email")
    actions = [approve_users]

    @admin.display(description="Approval Status")
    def approval_status(self, obj):
        if obj.is_approved:
            return "✅ Approved"
        return "⏳ Pending Approval"

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
    list_display = (
        'farmer', 'activity_type', 'date', 'farm_location',
        'farm_size', 'crop_type', 'date_planted', 'harvest_date',
        'expected_yield_kg', 'seeds_planted_kg', 'created_by',
    )
    search_fields = ('farmer__username', 'created_by__username', 'farm_location', 'crop_type')
    list_filter = ('activity_type',)

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





