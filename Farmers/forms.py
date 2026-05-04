from django import forms
from .models import Farmer, UserProfile


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


class CreateUserForm(forms.Form):
    ROLE_CHOICES = [
        ("investor", "Partner"),
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
