from django import forms
from pathlib import Path
from .models import (
    Farmer, UserProfile, FarmActivity, FarmAssessmentSheet1, FarmAssessmentSheet2, FarmAssessmentSheet3
)


class FarmerCreateByAgentForm(forms.Form):
    HOUSEHOLD_CHOICES = [
        ("1-2", "1-2 people"),
        ("3-5", "3-5 people"),
        ("6-8", "6-8 people"),
        ("9+", "9+ people"),
    ]
    YES_NO = [("yes", "Yes"), ("no", "No")]
    LAND_OWNERSHIP_CHOICES = [
        ("own", "Me"),
        ("family", "Family"),
        ("rented", "Rented"),
        ("community", "Community"),
    ]
    FARM_SIZE_CHOICES = [
        ("small", "Small (less than 2 acres)"),
        ("medium", "Medium (2-5 acres)"),
        ("large", "Large (more than 5 acres)"),
    ]
    YEAR_CHOICES = [(y, str(y)) for y in range(1970, __import__('datetime').date.today().year + 1)][::-1]
    TREE_AGE_CHOICES = [
        ("young", "Young"),
        ("mature", "Mature"),
        ("old", "Old"),
    ]
    SHADE_CHOICES = [
        ("none", "None"),
        ("few", "Few"),
        ("many", "Many"),
    ]
    SHADE_TYPES = [
        ("fruit", "Fruit trees"),
        ("timber", "Timber trees"),
        ("mixed", "Mixed"),
    ]
    BURN_CHOICES = [
        ("never", "Never"),
        ("sometimes", "Sometimes"),
        ("often", "Often"),
    ]
    FERT_BAG_RANGE_CHOICES = [
        ("none", "None"),
        ("1-2", "1-2 bags"),
        ("3-5", "3-5 bags"),
        ("5+", "More than 5 bags"),
    ]
    HARVEST_CHOICES = [
        ("0-5", "0-5 bags"),
        ("6-10", "6-10 bags"),
        ("11-20", "11-20 bags"),
        ("21+", "21+ bags"),
    ]

    # Account essentials
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Farmer username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "farmer@example.com"}),
        help_text="Each farmer must have a unique email address.",
    )

    # Section A - Farmer Details
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "What is your full name?"}),
    )
    household_size = forms.ChoiceField(choices=HOUSEHOLD_CHOICES, widget=forms.RadioSelect)
    belongs_to_group = forms.ChoiceField(choices=YES_NO, widget=forms.RadioSelect)
    farmer_group_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Farmers group name"}),
    )

    # Section B - Farm Location
    latitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6, widget=forms.HiddenInput)
    longitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6, widget=forms.HiddenInput)
    location_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Farm area name (auto-filled or enter manually)"}),
    )
    location_confirmed = forms.ChoiceField(choices=YES_NO, widget=forms.RadioSelect)
    land_ownership = forms.ChoiceField(choices=LAND_OWNERSHIP_CHOICES, widget=forms.RadioSelect)

    # Section C/D/E/G - Farm Characteristics
    year_planted = forms.ChoiceField(
        choices=[("", "Not sure")] + [(y, str(y)) for y in range(1970, __import__('datetime').date.today().year + 1)][::-1],
        required=False,
        label="What year were the cocoa trees first planted?",
    )
    farm_size_category = forms.ChoiceField(choices=FARM_SIZE_CHOICES, widget=forms.RadioSelect)

    has_shade_trees = forms.ChoiceField(choices=SHADE_CHOICES, widget=forms.RadioSelect)
    shade_tree_types = forms.ChoiceField(choices=SHADE_TYPES, required=False, widget=forms.RadioSelect)
    uses_fertilizer = forms.ChoiceField(choices=YES_NO, widget=forms.RadioSelect)
    fertilizer_bag_range = forms.ChoiceField(choices=FERT_BAG_RANGE_CHOICES, required=False, widget=forms.RadioSelect)
    fertilizer_application = forms.ChoiceField(
        choices=[("hand", "By hand"), ("machine", "With machine")],
        required=False,
        widget=forms.RadioSelect,
    )
    burns_farm_waste = forms.ChoiceField(choices=BURN_CHOICES, widget=forms.RadioSelect)
    received_training = forms.ChoiceField(choices=YES_NO, widget=forms.RadioSelect)
    plants_trees = forms.ChoiceField(choices=YES_NO, widget=forms.RadioSelect)
    practices_agroforestry = forms.ChoiceField(
        choices=YES_NO,
        widget=forms.RadioSelect,
        label="Do you grow other trees with cocoa?",
    )

    # Section F - Harvest History (up to 3 years; JS shows/hides based on year_planted)
    harvest_y1_bags = forms.ChoiceField(
        choices=HARVEST_CHOICES,
        widget=forms.RadioSelect,
        label="Most recent season harvest",
    )
    harvest_y2_bags = forms.ChoiceField(
        choices=HARVEST_CHOICES,
        required=False,
        widget=forms.RadioSelect,
        label="Season before that",
    )
    harvest_y3_bags = forms.ChoiceField(
        choices=HARVEST_CHOICES,
        required=False,
        widget=forms.RadioSelect,
        label="Season before that",
    )
    photo_of_farmer = forms.ImageField(required=True)
    photo_of_farm = forms.ImageField(required=True)
    voice_note = forms.FileField(required=False)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if Farmer.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "A farmer with this email address already exists. "
                "Each farmer must have a unique email."
            )
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if Farmer.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "A farmer with this username already exists."
            )
        return username

    def clean(self):
        cleaned_data = super().clean()

        belongs_to_group = cleaned_data.get("belongs_to_group")
        farmer_group_name = (cleaned_data.get("farmer_group_name") or "").strip()
        has_shade_trees = cleaned_data.get("has_shade_trees")
        shade_tree_types = cleaned_data.get("shade_tree_types")
        uses_fertilizer = cleaned_data.get("uses_fertilizer")
        fertilizer_application = cleaned_data.get("fertilizer_application")
        fertilizer_bag_range = cleaned_data.get("fertilizer_bag_range")
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")
        location_name = (cleaned_data.get("location_name") or "").strip()
        location_confirmed = cleaned_data.get("location_confirmed")

        if belongs_to_group == "yes" and not farmer_group_name:
            self.add_error("farmer_group_name", "Please provide the farmers group name.")

        if has_shade_trees in ["few", "many"] and not shade_tree_types:
            self.add_error("shade_tree_types", "Select the dominant shade tree type.")

        if uses_fertilizer == "yes":
            if not fertilizer_application:
                self.add_error("fertilizer_application", "Select how fertilizer is applied.")
            if not fertilizer_bag_range:
                self.add_error("fertilizer_bag_range", "Select fertilizer quantity range.")
        else:
            cleaned_data["fertilizer_application"] = ""
            cleaned_data["fertilizer_bag_range"] = "none"

        if not latitude or not longitude:
            raise forms.ValidationError("Tap to capture farm location before submitting.")

        if not location_name:
            self.add_error(
                "location_name",
                "Enter the farm place name manually if GPS could not detect it.",
            )

        if location_confirmed != "yes":
            self.add_error("location_confirmed", "Please confirm the captured farm area.")

        cleaned_data["location_name"] = location_name

        return cleaned_data


class CreateUserForm(forms.Form):
    ROLE_CHOICES = [
        ("investor", "Partner"),
        ("analyst", "Analyst"),
        ("admin", "Admin"),
        ("field_agent", "Field Agent"),
    ]

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "user@example.com"}),
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "First name (optional)"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Last name (optional)"}),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if Farmer.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if Farmer.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username


class FarmerRegistrationRequestForm(forms.Form):
    farmer_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Full name of farmer"}),
    )
    farmer_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "farmer@example.com (optional)"}),
    )
    farmer_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Phone number (optional)"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"placeholder": "Additional notes for the field agent...", "rows": 3}),
    )
    assigned_agent = forms.ModelChoiceField(
        queryset=None,
        empty_label="— Select a Field Agent —",
        label="Assign to Field Agent",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_agent"].queryset = Farmer.objects.filter(
            profile__role="field_agent", is_active=True
        ).order_by("username")


class PasswordResetRequestForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Your username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Your account email"}),
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip()

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()


class HomeContactForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Your full name"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}),
    )
    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={"placeholder": "+231 77 000 0000"}),
    )
    nationel = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "Nationality"}),
        label="Nationel",
    )
    current_resident = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "Current country of residence"}),
    )
    reason_for_contact = forms.CharField(
        max_length=1200,
        widget=forms.Textarea(attrs={"placeholder": "Tell us why you want to contact 1847 Ventures.", "rows": 4}),
    )


class InvestorDatasetUploadForm(forms.Form):
    dataset_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Optional dataset name"}),
    )
    data_file = forms.FileField(
        help_text="Upload Excel (.xlsx), CSV (.csv), or JSON (.json) file.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,.xlsx,.json"}),
    )

    def clean_data_file(self):
        data_file = self.cleaned_data["data_file"]
        extension = Path(data_file.name).suffix.lower()
        if extension not in {".csv", ".xlsx", ".json"}:
            raise forms.ValidationError("Unsupported file type. Upload .csv, .xlsx, or .json files only.")
        return data_file


class FarmerActivitySubmissionForm(forms.ModelForm):
    class Meta:
        model = FarmActivity
        fields = [
            "activity_type",
            "date",
            "additional_trees_added",
            "tool_changed_from",
            "tool_changed_to",
            "habit_changed_from",
            "habit_changed_to",
            "inputs_used",
            "quantity",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "inputs_used": forms.Textarea(attrs={"rows": 2, "placeholder": "Fertilizer, pruning tools, labor support, etc."}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Brief activity notes from this week."}),
            "tool_changed_from": forms.TextInput(attrs={"placeholder": "Previous tool (optional)"}),
            "tool_changed_to": forms.TextInput(attrs={"placeholder": "Current tool"}),
            "habit_changed_from": forms.TextInput(attrs={"placeholder": "Previous habit (optional)"}),
            "habit_changed_to": forms.TextInput(attrs={"placeholder": "New habit"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        activity_type = cleaned_data.get("activity_type")

        additional_trees_added = cleaned_data.get("additional_trees_added") or 0
        tool_changed_to = (cleaned_data.get("tool_changed_to") or "").strip()
        habit_changed_to = (cleaned_data.get("habit_changed_to") or "").strip()

        if activity_type == "additional_trees" and additional_trees_added <= 0:
            self.add_error("additional_trees_added", "Enter how many additional trees were added.")

        if activity_type == "tool_change" and not tool_changed_to:
            self.add_error("tool_changed_to", "Enter the new tool now being used.")

        if activity_type == "habit_change" and not habit_changed_to:
            self.add_error("habit_changed_to", "Enter the new farming habit.")

        cleaned_data["tool_changed_from"] = (cleaned_data.get("tool_changed_from") or "").strip()
        cleaned_data["tool_changed_to"] = tool_changed_to
        cleaned_data["habit_changed_from"] = (cleaned_data.get("habit_changed_from") or "").strip()
        cleaned_data["habit_changed_to"] = habit_changed_to
        return cleaned_data


# =================================================
# THREE-SHEET FARM ASSESSMENT FORMS
# See → Ask → Select Principle
# =================================================

class FarmAssessmentSheet1Form(forms.ModelForm):
    """SHEET 1: Farmer Profile & Location"""
    
    class Meta:
        model = FarmAssessmentSheet1
        fields = [
            "full_name",
            "household_size",
            "belongs_to_group",
            "farmer_group_name",
            "latitude",
            "longitude",
            "location_name",
            "land_ownership",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Full name",
                "class": "form-input"
            }),
            "household_size": forms.RadioSelect(attrs={"class": "form-radio"}),
            "belongs_to_group": forms.RadioSelect(attrs={"class": "form-radio"}),
            "farmer_group_name": forms.TextInput(attrs={
                "placeholder": "Farmers group name (if yes)",
                "class": "form-input"
            }),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "location_name": forms.TextInput(attrs={
                "placeholder": "Farm area name (auto-filled from GPS)",
                "class": "form-input",
                "readonly": "readonly"
            }),
            "land_ownership": forms.RadioSelect(attrs={"class": "form-radio"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        belongs_to_group = cleaned_data.get("belongs_to_group")
        farmer_group_name = (cleaned_data.get("farmer_group_name") or "").strip()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if belongs_to_group == "yes" and not farmer_group_name:
            self.add_error("farmer_group_name", "Please provide the farmers group name.")

        if not latitude or not longitude:
            raise forms.ValidationError("Capture the farmer GPS location before continuing.")

        cleaned_data["farmer_group_name"] = farmer_group_name
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.gps_captured = bool(instance.latitude and instance.longitude)
        if commit:
            instance.save()
        return instance


class FarmAssessmentSheet2Form(forms.ModelForm):
    """SHEET 2: Farm Assessment (Size, Trees, Activities)"""
    
    class Meta:
        model = FarmAssessmentSheet2
        fields = [
            "farm_size_category",
            "has_shade_trees",
            "shade_tree_types",
            "uses_fertilizer",
            "fertilizer_bag_range",
            "fertilizer_application",
            "burns_farm_waste",
            "practices_agroforestry",
            "received_training",
            "plants_trees",
        ]
        widgets = {
            "farm_size_category": forms.RadioSelect(attrs={"class": "form-radio"}),
            "has_shade_trees": forms.RadioSelect(attrs={"class": "form-radio"}),
            "shade_tree_types": forms.RadioSelect(attrs={"class": "form-radio"}),
            "uses_fertilizer": forms.RadioSelect(attrs={"class": "form-radio"}),
            "fertilizer_bag_range": forms.RadioSelect(attrs={"class": "form-radio"}),
            "fertilizer_application": forms.RadioSelect(attrs={"class": "form-radio"}),
            "burns_farm_waste": forms.RadioSelect(attrs={"class": "form-radio"}),
            "practices_agroforestry": forms.RadioSelect(attrs={"class": "form-radio"}),
            "received_training": forms.RadioSelect(attrs={"class": "form-radio"}),
            "plants_trees": forms.RadioSelect(attrs={"class": "form-radio"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        has_shade_trees = cleaned_data.get("has_shade_trees")
        shade_tree_types = cleaned_data.get("shade_tree_types")
        uses_fertilizer = cleaned_data.get("uses_fertilizer")
        fertilizer_bag_range = cleaned_data.get("fertilizer_bag_range")
        fertilizer_application = cleaned_data.get("fertilizer_application")

        if has_shade_trees in {"few", "many"} and not shade_tree_types:
            self.add_error("shade_tree_types", "Select the dominant shade tree type.")
        elif has_shade_trees == "none":
            cleaned_data["shade_tree_types"] = ""

        if uses_fertilizer == "yes":
            if not fertilizer_bag_range or fertilizer_bag_range == "none":
                self.add_error("fertilizer_bag_range", "Select the fertilizer quantity range.")
            if not fertilizer_application or fertilizer_application == "none":
                self.add_error("fertilizer_application", "Select how fertilizer is applied.")
        else:
            cleaned_data["fertilizer_bag_range"] = "none"
            cleaned_data["fertilizer_application"] = ""

        return cleaned_data


class FarmAssessmentSheet3Form(forms.ModelForm):
    """SHEET 3: Verification & Evidence (Photos, Voice Notes)"""
    
    class Meta:
        model = FarmAssessmentSheet3
        fields = [
            "harvest_history",
            "photo_of_farmer",
            "photo_of_farm",
            "photo_of_cocoa_trees",
            "photo_of_shade_trees",
            "voice_note",
            "validation_notes",
        ]
        widgets = {
            "harvest_history": forms.HiddenInput(),
            "photo_of_farmer": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "image/*"
            }),
            "photo_of_farm": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "image/*"
            }),
            "photo_of_cocoa_trees": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "image/*"
            }),
            "photo_of_shade_trees": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "image/*"
            }),
            "voice_note": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "audio/*"
            }),
            "validation_notes": forms.Textarea(attrs={
                "placeholder": "Any validation notes or anomalies...",
                "rows": 3,
                "class": "form-textarea"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        photo_of_farmer = cleaned_data.get("photo_of_farmer") or getattr(self.instance, "photo_of_farmer", None)
        photo_of_farm = cleaned_data.get("photo_of_farm") or getattr(self.instance, "photo_of_farm", None)

        if not photo_of_farmer:
            self.add_error("photo_of_farmer", "Upload the required farmer photo.")

        if not photo_of_farm:
            self.add_error("photo_of_farm", "Upload the required farm photo.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.photos_complete = bool(instance.photo_of_farmer and instance.photo_of_farm)
        if commit:
            instance.save()
        return instance
