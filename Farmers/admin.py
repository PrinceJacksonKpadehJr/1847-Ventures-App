from django.contrib import admin
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
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

# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('username', 'farmer_id', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'farmer_id', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

# ===== Register User Profile =======
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_approved")
    list_filter = ("is_approved", "role")
    search_fields = ("user__username", "user__email")

    def save_model(self, request, obj, form, change):
        # Detect the False → True transition for is_approved
        approval_just_granted = (
            change
            and "is_approved" in form.changed_data
            and obj.is_approved
        )
        if approval_just_granted:
            # Signal the post_save handler to skip its own notification so
            # this admin method remains the single source of the approval message.
            obj._approval_handled_by_admin = True
        super().save_model(request, obj, form, change)
        if approval_just_granted:
            self._handle_approval(request, obj)

    def _handle_approval(self, request, profile):
        """Generate a password-setup link and surface it to admin + create in-app message."""
        farmer = profile.user
        uid = urlsafe_base64_encode(force_bytes(farmer.pk))
        token = default_token_generator.make_token(farmer)
        setup_path = reverse(
            "farmer_set_password", kwargs={"uidb64": uid, "token": token}
        )
        setup_url = request.build_absolute_uri(setup_path)

        # Show the link to the admin in the UI
        self.message_user(
            request,
            (
                f"Account for '{farmer.username}' approved. "
                f"Password setup link: {setup_url} — "
                "An in-app message has been sent to the farmer."
            ),
            level="success",
        )

        # Create in-app Message so the farmer sees it on first login
        Message.objects.create(
            sender=request.user,
            receiver=farmer,
            content=(
                "Your 1847 Ventures account has been approved!\n\n"
                f"Please set your password by visiting:\n{setup_url}\n\n"
                "Once you have set your password you can log in normally."
            ),
        )

        # Try to send email if the farmer has one
        if farmer.email:
            from django.core.mail import send_mail
            from django.conf import settings as django_settings

            try:
                send_mail(
                    subject="Your 1847 Ventures account is approved – set your password",
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
                pass

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




