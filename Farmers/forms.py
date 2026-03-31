from django import forms
from django.contrib.auth import get_user_model


class CreateFarmerForm(forms.Form):
    """
    Used by field agents to register a new farmer.
    The farmer can supply an existing email address or create a new one.
    A password is NOT set here; the farmer receives a setup link after admin approval.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Farmer username"}),
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Farmer email address"}),
        help_text=(
            "The farmer can use an existing email address or create a new one. "
            "A password-setup link will be sent to this address after admin approval."
        ),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "A farmer with this username already exists. Please choose a different username."
            )
        return username
