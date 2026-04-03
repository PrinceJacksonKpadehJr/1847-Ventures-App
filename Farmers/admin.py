from django.contrib import admin
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


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fields = ("role", "email", "is_approved")
    extra = 0


# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'farmer_id', 'phone_number', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'farmer_id', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')


# ===== Register User Profile =======
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "role", "is_approved")
    list_filter = ("role", "is_approved")
    search_fields = ("user__username", "email")
    actions = ["approve_selected"]

    def approve_selected(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} user(s) approved.")
    approve_selected.short_description = "Approve selected users"

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




