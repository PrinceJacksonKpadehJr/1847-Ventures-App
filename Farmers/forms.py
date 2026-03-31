from django import forms
from .models import Farmer


class FarmerRegistrationForm(forms.Form):
    """Used by field agents to register a new farmer (username only; no password)."""

    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={"placeholder": "Enter username"}),
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label="First Name",
        widget=forms.TextInput(attrs={"placeholder": "First name (optional)"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label="Last Name",
        widget=forms.TextInput(attrs={"placeholder": "Last name (optional)"}),
    )
    email = forms.EmailField(
        required=False,
        label="Email (optional)",
        widget=forms.EmailInput(attrs={"placeholder": "farmer@example.com"}),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        label="Phone Number",
        widget=forms.TextInput(attrs={"placeholder": "Phone number (optional)"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if Farmer.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username


class FarmActivityForm(forms.Form):
    """Used by field agents to log a farm activity record for an existing farmer."""

    farmer = forms.ModelChoiceField(
        queryset=Farmer.objects.none(),
        label="Farm Owner",
        empty_label="-- Select Farmer --",
    )
    farm_name = forms.CharField(
        max_length=255,
        label="Farm Name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Green Valley Farm"}),
    )
    location = forms.CharField(
        max_length=255,
        label="Farm Location",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Ashanti Region, Ghana"}),
    )
    size_in_hectares = forms.FloatField(
        label="Farm Size (hectares)",
        min_value=0.0,
        widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
    )
    crop_name = forms.CharField(
        max_length=100,
        label="Type of Crops",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Cocoa, Maize"}),
    )
    date_planted = forms.DateField(
        label="Date Planted",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    approx_harvest_date = forms.DateField(
        label="Approximate Harvest Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    expected_yield_kg = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        label="Expected Yield (kg)",
        min_value=0,
        widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
    )
    seeds_planted_kg = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        label="Seeds Planted (kg)",
        min_value=0,
        widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only list approved farmers with role='farmer'
        self.fields["farmer"].queryset = Farmer.objects.filter(
            profile__role="farmer"
        ).order_by("username")
