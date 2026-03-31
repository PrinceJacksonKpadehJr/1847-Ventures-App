from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import Farmer, UserProfile, FarmActivity


class CreateFarmerForm(forms.Form):
    """Form used by field agents to create a new farmer account."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Leave blank to auto-generate a password.",
        required=False,
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if Farmer.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password


class FarmActivityForm(forms.ModelForm):
    """Form for recording a farm activity, used by field agents."""

    class Meta:
        model = FarmActivity
        fields = [
            "farmer",
            "activity_type",
            "farm_location",
            "farm_size",
            "crop_type",
            "date_planted",
            "harvest_date",
            "expected_yield_kg",
            "seeds_planted_kg",
            "date",
            "inputs_used",
            "quantity",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "date_planted": forms.DateInput(attrs={"type": "date"}),
            "harvest_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "farm_size": "Farm Size (hectares)",
            "expected_yield_kg": "Expected Yield (kg)",
            "seeds_planted_kg": "Seeds Planted (kg)",
            "date": "Activity Date",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show approved farmers in the farmer dropdown
        self.fields["farmer"].queryset = Farmer.objects.filter(
            profile__role="farmer",
            profile__is_approved=True,
        )
        self.fields["farmer"].label = "Farm Owner (Farmer)"
