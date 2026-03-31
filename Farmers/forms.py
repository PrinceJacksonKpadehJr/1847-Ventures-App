from django import forms
from .models import Farmer


class FarmerCreateByAgentForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Username", "class": "form-input"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Email address", "class": "form-input"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if Farmer.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Farmer.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email address already exists.")
        return email
