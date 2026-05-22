from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile, FarmReport
from .models import Farmer, UserProfile

Farmer = get_user_model()

class FarmerCreateByAgentForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if UserProfile.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already used.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if Farmer.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

class FarmReportForm(forms.ModelForm):
    class Meta:
        model = FarmReport
        fields = [
            'farmer', 'farm_location', 'farm_size',
            'crop_type', 'date_planted', 'approx_harvest_date',
            'expected_yield_kg', 'seeds_planted_kg'
        ]

def clean_email(self):
    email = self.cleaned_data["email"].lower().strip()
    if Farmer.objects.filter(email__iexact=email).exists():
        raise forms.ValidationError(
            "A farmer with this email address already exists. "
            "Each farmer must have a unique email."
        )
    return email