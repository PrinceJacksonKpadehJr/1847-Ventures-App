from django.contrib import admin
from django.contrib import messages as django_messages
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.conf import settings
import logging
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
    Message,
    PasswordResetRequest,
)

logger = logging.getLogger(__name__)

# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('username', 'farmer_id', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'farmer_id', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

# ===== Register User Profile =======
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_approved")
    list_filter = ("is_approved",)
    search_fields = ("user__username", "user__email")

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


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ("requester", "requested_at", "is_otp_sent", "otp_sent_at", "send_otp_button")
    search_fields = ("requester__username", "requester__email")
    list_filter = ("is_otp_sent", "requested_at")
    readonly_fields = ("otp_code", "otp_sent_at", "otp_expires_at", "requested_at")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:request_id>/send-otp/",
                self.admin_site.admin_view(self.send_otp_view),
                name="farmers_passwordresetrequest_send_otp",
            ),
        ]
        return custom_urls + urls

    def send_otp_button(self, obj):
        if obj.is_otp_sent:
            return "OTP sent"
        url = reverse("admin:farmers_passwordresetrequest_send_otp", args=[obj.id])
        return format_html('<a class="button" href="{}">Send OTP</a>', url)

    send_otp_button.short_description = "Action"

    def send_otp_view(self, request, request_id):
        password_request = get_object_or_404(PasswordResetRequest, id=request_id)
        changelist_url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist"
        )

        if not password_request.requester.email:
            self.message_user(
                request,
                "Requester has no email address.",
                level=django_messages.ERROR,
            )
            return redirect(changelist_url)

        otp = password_request.generate_otp()

        try:
            send_mail(
                subject="Your password reset OTP",
                message=f"Your OTP for password reset is {otp}. It expires in 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[password_request.requester.email],
                fail_silently=False,
            )
            password_request.is_otp_sent = True
            password_request.otp_sent_at = timezone.now()
            password_request.save(update_fields=["otp_code", "otp_expires_at", "is_otp_sent", "otp_sent_at"])
            self.message_user(request, f"OTP sent to {password_request.requester.email}.")
        except Exception:
            logger.exception("Failed sending OTP email for password reset request %s", password_request.id)
            self.message_user(
                request,
                "OTP could not be sent because email delivery failed.",
                level=django_messages.ERROR,
            )
        return redirect(changelist_url)
