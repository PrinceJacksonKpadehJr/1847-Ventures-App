from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from .models import Message, Announcement
from .serializers import MessageSerializer
from Farmers.decorators import approved_user_required
from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from Farmers.models import UserProfile
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Sum
from .forms import CreateFarmerForm







from .models import Farmer, Farm, Harvest, Investment, FarmActivity, Announcement
from .serializers import (
    FarmerSerializer,
    FarmSerializer,
    HarvestSerializer,
    InvestmentSerializer,
    FarmActivitySerializer,
    AnnouncementSerializer,
    FarmerRegistrationSerializer
)
# -------------------------------
# Farmer ViewSet
# -------------------------------
class FarmerViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Farmer.objects.all()
        elif user.role == 'field_agent':
            return Farmer.objects.filter(created_by=user)
        return Farmer.objects.filter(id=user.id)  # Farmer sees only self

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create a farmer.")


# -------------------------------
# Farm ViewSet
# -------------------------------
class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Farm.objects.all()
        elif user.role == 'field_agent':
            return Farm.objects.filter(farmer__created_by=user)
        elif user.role == 'farmer':
            return Farm.objects.filter(farmer=user)
        return Farm.objects.none()  # Investors cannot modify farms

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create a farm.")


# -------------------------------
# Harvest ViewSet
# -------------------------------
class HarvestViewSet(viewsets.ModelViewSet):
    serializer_class = HarvestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Harvest.objects.all()
        elif user.role == 'field_agent':
            return Harvest.objects.filter(farm__farmer__created_by=user)
        elif user.role == 'farmer':
            return Harvest.objects.filter(farm__farmer=user)
        elif user.role == 'investor':
            return Harvest.objects.all()
        return Harvest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent', 'farmer']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create a harvest.")


# -------------------------------
# Investment ViewSet
# -------------------------------
class InvestmentViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Investment.objects.all()
        elif user.role == 'investor':
            return Investment.objects.filter(farmer=user)
        elif user.role == 'farmer':
            return Investment.objects.filter(farmer=user)
        return Investment.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'investor']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create an investment.")


# -------------------------------
# FarmActivity ViewSet
# -------------------------------
class FarmActivityViewSet(viewsets.ModelViewSet):
    serializer_class = FarmActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return FarmActivity.objects.all()
        elif user.role == 'field_agent':
            return FarmActivity.objects.filter(farmer__created_by=user)
        elif user.role == 'farmer':
            return FarmActivity.objects.filter(farmer=user)
        elif user.role == 'investor':
            return FarmActivity.objects.all()
        return FarmActivity.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role in ['admin', 'field_agent', 'farmer']:
            serializer.save()
        else:
            raise PermissionDenied("You do not have permission to create farm activity.")


# -------------------------------
# Farmer Registration (public)
# -------------------------------
class FarmerRegistrationView(generics.CreateAPIView):
    serializer_class = FarmerRegistrationSerializer
    permission_classes = []  # Public endpoint

# -------------------------------
# Announcements ViewSet (read-only)
# -------------------------------
class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns a list of active announcements
    """
    queryset = Announcement.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = AnnouncementSerializer


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Message.objects.all()

        if user.role in ['field_agent', 'farmer']:
            return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)

        return Message.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        receiver = serializer.validated_data['receiver']

        if user.role == 'farmer' and receiver.is_superuser:
            raise PermissionDenied("Farmers cannot message admin.")

        if user.role == 'farmer' and receiver.role != 'field_agent':
            raise PermissionDenied("Farmers can only message field agents.")

        serializer.save(sender=user)


@approved_user_required
def dashboard(request):
    return render(request, "Farmers/dashboard.html")

from django.shortcuts import render

def home(request):
    return render(request, "Farmers/home.html")

class CustomLoginView(LoginView):
    template_name = "Farmers/login.html"

    def form_valid(self, form):
        user = form.get_user()

        # Ensure profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)

        # Block unapproved users (except superuser)
        if not user.is_superuser and not profile.is_approved:
            messages.error(self.request, "Your account is not yet approved.")
            return redirect('login')

        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user

        # Ensure profile exists again safely
        profile, created = UserProfile.objects.get_or_create(user=user)

        if user.is_superuser:
            return reverse_lazy('admin:index')

        role = profile.role

        if role == 'farmer':
            return reverse_lazy('farmer_dashboard')

        if role == 'field_agent':
            return reverse_lazy('agent_dashboard')

        if role == 'investor':
            return reverse_lazy('partner_dashboard')

        return reverse_lazy('home')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('home')

@login_required
def farmer_dashboard(request):
    if not hasattr(request.user, "profile") or request.user.profile.role != "farmer":
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/farmer_dashboard.html")


@login_required
def agent_dashboard(request):
    if not hasattr(request.user, "profile") or request.user.profile.role != "field_agent":
        return HttpResponseForbidden("Access Denied")
    User = get_user_model()
    farmers = User.objects.filter(
        profile__role="farmer"
    ).select_related("profile").order_by("-date_joined")
    form = CreateFarmerForm()
    return render(request, "Farmers/agent_dashboard.html", {
        "farmers": farmers,
        "form": form,
    })


@login_required
def partner_dashboard(request):
    if not hasattr(request.user, "profile") or request.user.profile.role != "investor":
        return HttpResponseForbidden("Access Denied")
    investments = (
        Investment.objects
        .filter(investor=request.user)
        .select_related("farm")
        .order_by("-invested_at")
    )
    total_invested = investments.aggregate(total=Sum("amount"))["total"] or 0
    announcements = Announcement.objects.filter(is_active=True).order_by("-created_at")[:10]
    return render(request, "Farmers/partner_dashboard.html", {
        "investments": investments,
        "total_invested": total_invested,
        "announcements": announcements,
    })


@login_required
def create_farmer(request):
    """
    Allows a field agent to register a new farmer with username + email.
    The farmer receives a password-setup email after admin approval.
    Farmers may supply an existing email address or create a new one.
    """
    if not hasattr(request.user, "profile") or request.user.profile.role != "field_agent":
        return HttpResponseForbidden("Access Denied")

    User = get_user_model()

    if request.method == "POST":
        form = CreateFarmerForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]

            # Warn if the email is already associated with an existing account,
            # but allow it — farmers may reuse an existing email address.
            if User.objects.filter(email__iexact=email).exists():
                messages.warning(
                    request,
                    f"Note: the email '{email}' is already associated with another account. "
                    "The farmer can still use this address — both accounts will receive "
                    "their own password-setup link.",
                )

            farmer = User(username=username, email=email)
            farmer.set_unusable_password()
            farmer.save()

            profile, _ = UserProfile.objects.get_or_create(user=farmer)
            profile.role = "farmer"
            profile.is_approved = False
            profile.save()

            messages.success(
                request,
                f"Farmer '{username}' registered successfully. "
                "The account is pending admin approval. "
                "Once approved, the farmer will receive a password-setup link at "
                f"'{email}'.",
            )
            return redirect("agent_dashboard")
    else:
        form = CreateFarmerForm()

    farmers = User.objects.filter(
        profile__role="farmer"
    ).select_related("profile").order_by("-date_joined")
    return render(request, "Farmers/agent_dashboard.html", {
        "farmers": farmers,
        "form": form,
    })