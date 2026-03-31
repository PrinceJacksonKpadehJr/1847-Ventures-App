from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


# =================================================
# Custom User Model
# =================================================
class Farmer(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    farmer_id = models.CharField(
        max_length=50,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )

    registration_date = models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(
        Group,
        related_name="farmer_set",
        blank=True
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="farmer_permissions_set",
        blank=True
    )

    def __str__(self):
        return self.username


# =================================================
# User Profile (Roles + Approval)
# =================================================
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("farmer", "Farmer"),
        ("investor", "Investor"),
        ("field_agent", "Field Agent"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="farmer"
    )

    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


# Farm
# =================================================
class Farm(models.Model):
    name = models.CharField(max_length=255, default="Unknown Farm")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="farms"
    )
    location = models.CharField(max_length=255, default= "Unknown")
    size_in_hectares = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.owner.username})"


# Crop
# =================================================
class Crop(models.Model):
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="crops"
    )
    name = models.CharField(max_length=100)
    planting_date = models.DateField()
    harvest_date = models.DateField(null=True, blank=True)
    expected_yield_kg = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} on {self.farm.name}"


# =================================================
# Harvest
# =================================================
class Harvest(models.Model):
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="harvests"
    )
    date_of_harvest = models.DateField()
    tons_produced = models.FloatField()
    quality_grade = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.farm.name} - {self.date_of_harvest}"


# =================================================
# Investment
# =================================================
class Investment(models.Model):
    investor = models.ForeignKey(
        Farmer,
        on_delete=models.CASCADE,
        related_name="investments_made",
        null=True,
        blank=True
    )

    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="investments",
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    expected_return_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    invested_at = models.DateTimeField(auto_now_add=True)


# =================================================
# Farm Activity
# =================================================
class FarmActivity(models.Model):
    ACTIVITY_CHOICES = [
        ("planting", "Planting"),
        ("pruning", "Pruning"),
        ("spraying", "Spraying"),
        ("harvesting", "Harvesting"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    # Field agent who recorded this activity
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="recorded_activities",
        null=True,
        blank=True,
    )

    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    date = models.DateField()
    inputs_used = models.TextField(blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Extended fields for full farm activity recording
    farm_location = models.CharField(max_length=255, blank=True, null=True)
    farm_size = models.FloatField(blank=True, null=True, help_text="Size in hectares")
    crop_type = models.CharField(max_length=100, blank=True, null=True)
    date_planted = models.DateField(blank=True, null=True)
    harvest_date = models.DateField(blank=True, null=True, help_text="Approximate harvest date")
    expected_yield_kg = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Expected yield in kg"
    )
    seeds_planted_kg = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Seeds planted in kg"
    )

    def __str__(self):
        return f"{self.farmer.username} - {self.activity_type}"


# =================================================
# Announcement
# =================================================
class Announcement(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


# =================================================
# Messaging
# =================================================
class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"


# =================================================
# Signals
# =================================================
@receiver(post_save, sender=Farmer)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
