from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import IntegrityError
import uuid


# =================================================
# Custom User Model
# =================================================
class Farmer(AbstractUser):
    email = models.EmailField(unique=True, verbose_name="email address")
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
        ("analyst", "Analyst"),
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

    must_change_password = models.BooleanField(default=False)

    created_by_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="farmers_created"
    )

    profile_photo = models.FileField(
        upload_to="profile_pictures/",
        null=True,
        blank=True
    )

    dashboard_layout = models.JSONField(default=dict, blank=True)

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
        ("additional_trees", "Additional Trees Added"),
        ("tool_change", "Change of Tool"),
        ("habit_change", "Change of Habit"),
        ("planting", "Planting"),
        ("pruning", "Pruning"),
        ("spraying", "Spraying"),
        ("harvesting", "Harvesting"),
    ]

    VERIFICATION_STATUS_CHOICES = [
        ("pending", "Pending Field Agent Verification"),
        ("verified", "Verified by Field Agent"),
        ("rejected", "Rejected by Field Agent"),
    ]

    ADMIN_APPROVAL_STATUS_CHOICES = [
        ("pending", "Pending Admin Approval"),
        ("approved", "Approved by Admin"),
        ("rejected", "Rejected by Admin"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    date = models.DateField()
    inputs_used = models.TextField(blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    additional_trees_added = models.PositiveIntegerField(default=0)
    tool_changed_from = models.CharField(max_length=150, blank=True)
    tool_changed_to = models.CharField(max_length=150, blank=True)
    habit_changed_from = models.CharField(max_length=200, blank=True)
    habit_changed_to = models.CharField(max_length=200, blank=True)

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default="pending",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_farm_activities",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    agent_verification_notes = models.TextField(blank=True)

    admin_approval_status = models.CharField(
        max_length=20,
        choices=ADMIN_APPROVAL_STATUS_CHOICES,
        default="pending",
    )
    admin_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_reviewed_farm_activities",
    )
    admin_reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.farmer.username} - {self.activity_type}"


# =================================================
# Announcement
# =================================================
class Announcement(models.Model):
    AUDIENCE_CHOICES = [
        ("all_farmers", "All Farmers"),
        ("all_field_agents", "All Field Agents"),
        ("all", "Everyone (Farmers & Field Agents)"),
        ("agent_farmers", "Agent's Farmers"),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Broadcast targeting
    target_audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default="all",
    )
    # Used when target_audience == "agent_farmers": points to the broadcasting field agent
    target_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_announcements",
    )

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
# Notification (for messages and announcements)
# =================================================
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'Direct Message'),
        ('announcement', 'Announcement'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='message'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Links to related objects
    related_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_announcement = models.ForeignKey(
        'Announcement',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"


# =================================================
# Admin Notification
# =================================================
class AdminNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_farmer', 'New Farmer Submission'),
        ('info', 'Information'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='new_farmer'
    )
    message = models.TextField()
    related_farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_about'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:50]}"


class ContactSubmission(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    nationel = models.CharField(max_length=120)
    current_resident = models.CharField(max_length=120)
    reason_for_contact = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Contact submission: {self.name} ({self.email})"


# =================================================
# Farmer Registration Request
# =================================================
class FarmerRegistrationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farmer_requests_created'
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farmer_requests_assigned'
    )
    farmer_name = models.CharField(max_length=255)
    farmer_email = models.EmailField(blank=True)
    farmer_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request for {self.farmer_name} → {self.assigned_agent.username}"


class PasswordResetRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_requests",
    )
    requested_by_username = models.CharField(max_length=150)
    requested_by_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="password_reset_requests_processed",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Password reset request for {self.user.username} ({self.status})"


class FarmerDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ("otp_pending", "OTP Pending"),
        ("pending_partner_approval", "Pending Partner Approval"),
        ("rejected", "Rejected"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="farmer_deletion_requests_created",
    )
    partner_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="farmer_deletion_requests_reviewed",
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="otp_pending")
    otp_hash = models.CharField(max_length=255, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Deletion request: {self.farmer.username} ({self.status})"


class InvestorDatasetImport(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("imported", "Imported"),
        ("failed", "Failed"),
    ]

    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("xlsx", "XLSX"),
        ("json", "JSON"),
    ]

    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dataset_imports",
    )
    dataset_name = models.CharField(max_length=255)
    source_file = models.FileField(upload_to="investor_uploads/%Y/%m/%d/")
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    schema = models.JSONField(default=list, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    
    # Domain classification fields
    DOMAIN_CHOICES = [
        ("agriculture", "Agriculture/Farm Data"),
        ("finance", "Financial/Business Data"),
        ("hr", "Human Resources Data"),
        ("inventory", "Inventory/Logistics Data"),
        ("carbon_esg", "Carbon/ESG Data"),
        ("general", "General Analytics Data"),
        ("custom", "Custom/Unknown"),
    ]
    inferred_domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES, default="general", blank=True)
    inferred_domain_scores = models.JSONField(default=dict, blank=True)
    inferred_domain_confidence = models.FloatField(default=0.0, blank=True)
    confirmed_domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES, null=True, blank=True)

    # Data Preparation Workspace
    column_metadata = models.JSONField(default=dict, blank=True)  # {column_name: {rename, type, semantic_tag, hidden, ...}}
    row_operations = models.JSONField(default=dict, blank=True)  # {removed_rows: [], filtered_rows: [], ...}
    prep_history = models.JSONField(default=list, blank=True)  # Array of {operation, timestamp, data} for undo/redo
    prep_state = models.JSONField(default=dict, blank=True)  # Current state snapshot for live preview

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.dataset_name} ({self.status})"


class InvestorDatasetRow(models.Model):
    dataset = models.ForeignKey(
        InvestorDatasetImport,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_number = models.PositiveIntegerField()
    payload = models.JSONField(default=dict)
    fingerprint = models.TextField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["dataset", "fingerprint"]),
            models.Index(fields=["dataset", "row_number"]),
        ]


class DatasetAuditLog(models.Model):
    ACTION_CHOICES = [
        ("upload_preview", "Upload Preview"),
        ("api_ingest", "API Ingest"),
        ("incremental_upload", "Incremental Upload"),
        ("import", "Import"),
        ("discard", "Discard"),
        ("delete", "Delete"),
        ("load_existing", "Load Existing"),
        ("save_layout", "Save Layout"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dataset_audit_logs",
    )
    dataset = models.ForeignKey(
        InvestorDatasetImport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.actor.username} - {self.action}"


# =================================================
# Farm Assessment Data (Three-Sheet Structure)
# See → Ask → Select principle (no free text, no calculations)
# =================================================

class FarmAssessmentSheet1(models.Model):
    """SHEET 1: Farmer Profile & Location"""
    
    farmer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_sheet1"
    )
    
    # Farmer Details
    full_name = models.CharField(max_length=255)
    household_size = models.CharField(
        max_length=20,
        choices=[
            ("1-2", "1–2 people"),
            ("3-5", "3–5 people"),
            ("6-8", "6–8 people"),
            ("9+", "9+ people"),
        ]
    )
    belongs_to_group = models.CharField(
        max_length=10,
        choices=[("yes", "Yes"), ("no", "No")]
    )
    farmer_group_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Farm Location (GPS auto-capture)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_name = models.CharField(max_length=255, blank=True)
    gps_captured = models.BooleanField(default=False)
    
    # Land Ownership
    land_ownership = models.CharField(
        max_length=20,
        choices=[
            ("own", "Own"),
            ("family", "Family"),
            ("rented", "Rented"),
            ("community", "Community"),
        ]
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sheet1_assessments"
    )
    
    def __str__(self):
        return f"Sheet1: {self.farmer.username} - Profile & Location"


class FarmAssessmentSheet2(models.Model):
    """SHEET 2: Farm Assessment (Size, Trees, Activities)"""
    
    farmer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_sheet2"
    )
    
    # Farm Size (Observational Categories)
    farm_size_category = models.CharField(
        max_length=20,
        choices=[
            ("small", "Small (less than 2 acres)"),
            ("medium", "Medium (2–5 acres)"),
            ("large", "Large (more than 5 acres)"),
        ]
    )
    
    # Year farm was planted — critical for lifespan tracking (cocoa: 25-30 yrs)
    year_planted = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Year cocoa was first planted on this farm."
    )

    # Shade Trees (Carbon Critical)
    has_shade_trees = models.CharField(
        max_length=20,
        choices=[
            ("none", "None"),
            ("few", "Few trees"),
            ("many", "Many trees"),
        ]
    )
    shade_tree_types = models.CharField(
        max_length=100,
        choices=[
            ("fruit", "Fruit trees"),
            ("timber", "Timber trees"),
            ("mixed", "Mixed"),
        ],
        blank=True
    )
    
    # Farm Activities (Emissions-related)
    uses_fertilizer = models.CharField(
        max_length=10,
        choices=[("yes", "Yes"), ("no", "No")]
    )
    fertilizer_bag_range = models.CharField(
        max_length=20,
        choices=[
            ("none", "None"),
            ("1-2", "1-2 bags"),
            ("3-5", "3-5 bags"),
            ("5+", "More than 5 bags"),
        ],
        default="none",
    )
    fertilizer_application = models.CharField(
        max_length=20,
        choices=[
            ("none", "None"),
            ("hand", "By hand"),
            ("machine", "With machine"),
        ],
        blank=True
    )
    burns_farm_waste = models.CharField(
        max_length=20,
        choices=[
            ("never", "Never"),
            ("sometimes", "Sometimes"),
            ("often", "Often"),
        ]
    )
    practices_agroforestry = models.CharField(
        max_length=10,
        choices=[("yes", "Yes"), ("no", "No")]
    )
    
    # Training & Practices
    received_training = models.CharField(
        max_length=10,
        choices=[("yes", "Yes"), ("no", "No")]
    )
    plants_trees = models.CharField(
        max_length=10,
        choices=[("yes", "Yes"), ("no", "No")]
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sheet2_assessments"
    )
    
    def __str__(self):
        return f"Sheet2: {self.farmer.username} - Farm Assessment"


class FarmAssessmentSheet3(models.Model):
    """SHEET 3: Verification & Evidence (Photos, Voice Notes)"""
    
    farmer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_sheet3"
    )
    
    # Harvest history — dict keyed by year string, value is bag-range choice
    # e.g. {"2025": "11-20", "2024": "6-10", "2023": "0-5"}
    harvest_history = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-year harvest bag ranges collected at intake (up to 3 years)."
    )

    # Evidence Photos
    photo_of_farmer = models.ImageField(
        upload_to="farm_assessments/farmer_photos/",
        null=True,
        blank=True
    )
    photo_of_farm = models.ImageField(
        upload_to="farm_assessments/farm_photos/",
        null=True,
        blank=True
    )
    photo_of_cocoa_trees = models.ImageField(
        upload_to="farm_assessments/cocoa_photos/",
        null=True,
        blank=True
    )
    photo_of_shade_trees = models.ImageField(
        upload_to="farm_assessments/shade_photos/",
        null=True,
        blank=True
    )
    
    # Voice Note
    voice_note = models.FileField(
        upload_to="farm_assessments/voice_notes/",
        null=True,
        blank=True,
        help_text="Optional voice note from farmer"
    )
    
    # Verification Flags
    photos_complete = models.BooleanField(default=False)
    data_validated = models.BooleanField(default=False)
    validation_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sheet3_assessments"
    )
    
    def __str__(self):
        return f"Sheet3: {self.farmer.username} - Verification & Evidence"


# =================================================
# Signals
# =================================================
@receiver(post_save, sender=Farmer)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            UserProfile.objects.create(user=instance)
        except IntegrityError:
            # If the signal is connected more than once, profile may already exist.
            UserProfile.objects.filter(user=instance).first()


@receiver(post_save, sender=Message)
def create_notification_on_message(sender, instance, created, **kwargs):
    """Create a notification when a new message is sent."""
    if created:
        sender_name = instance.sender.first_name or instance.sender.username
        Notification.objects.create(
            recipient=instance.receiver,
            notification_type='message',
            title=f"New message from {sender_name}",
            message=instance.content[:100],
            related_message=instance
        )


@receiver(post_save, sender=Announcement)
def create_notification_on_announcement(sender, instance, created, **kwargs):
    """Create notifications for all recipients when an announcement is created."""
    if created:
        from django.db.models import Q
        
        # Determine who should receive this announcement
        recipients = set()
        
        if instance.target_audience == "all_farmers":
            # All farmers
            recipients = set(
                UserProfile.objects.filter(role="farmer")
                .values_list('user_id', flat=True)
            )
        elif instance.target_audience == "all_field_agents":
            # All field agents
            recipients = set(
                UserProfile.objects.filter(role="field_agent")
                .values_list('user_id', flat=True)
            )
        elif instance.target_audience == "all":
            # All farmers and field agents
            recipients = set(
                UserProfile.objects.filter(
                    Q(role="farmer") | Q(role="field_agent")
                ).values_list('user_id', flat=True)
            )
        elif instance.target_audience == "agent_farmers" and instance.target_agent:
            # Farmers under a specific agent
            recipients = set(
                UserProfile.objects.filter(created_by_agent=instance.target_agent)
                .values_list('user_id', flat=True)
            )
        
        # Don't send notification to the announcer
        recipients.discard(instance.created_by_id)
        
        # Create notifications for each recipient
        creator_name = instance.created_by.first_name or instance.created_by.username
        for recipient_id in recipients:
            Notification.objects.create(
                recipient_id=recipient_id,
                notification_type='announcement',
                title=f"Announcement from {creator_name}",
                message=instance.title,
                related_announcement=instance
            )
