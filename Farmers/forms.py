from django import forms
from .models import Farmer


class FarmerCreateByAgentForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Farmer username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "farmer@example.com"}),
        help_text="Each farmer must have a unique email address.",
    )

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
