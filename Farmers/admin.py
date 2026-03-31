from django.contrib import admin
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.translation import ngettext
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


def approve_farmers(modeladmin, request, queryset):
    """
    Admin action: approve selected farmer accounts and send each farmer a
    password-setup email.  Uses Django's token generator directly so that
    users with an unusable password (newly registered farmers) are also
    handled.  Farmers may have used an existing email address or a new one.
    """
    approved_count = 0
    emailed_count = 0
    no_email_count = 0

    protocol = "https" if request.is_secure() else "http"
    domain = request.get_host()

    for profile in queryset:
        profile.is_approved = True
        profile.save()
        approved_count += 1

        user = profile.user
        if user.email:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            context = {
                "email": user.email,
                "domain": domain,
                "uid": uid,
                "user": user,
                "token": token,
                "protocol": protocol,
            }
            subject = render_to_string(
                "registration/password_reset_subject.txt", context
            ).strip()
            body = render_to_string(
                "registration/password_reset_email.html", context
            )

            try:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                emailed_count += 1
            except Exception:
                pass
        else:
            no_email_count += 1

    msg = ngettext(
        "%d account approved.",
        "%d accounts approved.",
        approved_count,
    ) % approved_count

    if emailed_count:
        msg += " Password-setup email sent to %d farmer(s)." % emailed_count
    if no_email_count:
        msg += (
            " %d farmer(s) have no email address on file — "
            "please add an email so they can set a password." % no_email_count
        )

    modeladmin.message_user(request, msg)


approve_farmers.short_description = "Approve selected accounts and send password-setup email"


# ===== Custom Farmer Admin =====
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'farmer_id', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'farmer_id', 'first_name', 'last_name', 'email')
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
