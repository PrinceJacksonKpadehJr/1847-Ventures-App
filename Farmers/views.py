from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from .models import Message
from .serializers import MessageSerializer
from Farmers.decorators import approved_user_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from Farmers.models import UserProfile, FarmActivity
from django.shortcuts import redirect
from django.contrib import messages
import secrets
import string







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
    if not (request.user.is_superuser or
            getattr(getattr(request.user, 'profile', None), 'role', None) == 'farmer'):
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/farmer_dashboard.html")


@login_required
def agent_dashboard(request):
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or
            getattr(profile, 'role', None) == 'field_agent'):
        return HttpResponseForbidden("Access Denied")

    from .forms import CreateFarmerForm, FarmActivityForm

    farmer_form = CreateFarmerForm()
    activity_form = FarmActivityForm()

    # Recent farmers created by this agent
    recent_farmers = Farmer.objects.filter(
        profile__role='farmer'
    ).order_by('-registration_date')[:10]

    # Recent activities recorded by this agent
    recent_activities = FarmActivity.objects.filter(
        created_by=request.user
    ).order_by('-date')[:10]

    return render(request, "Farmers/agent_dashboard.html", {
        "farmer_form": farmer_form,
        "activity_form": activity_form,
        "recent_farmers": recent_farmers,
        "recent_activities": recent_activities,
    })


@login_required
def create_farmer(request):
    """Field agent creates a new farmer account (pending admin approval)."""
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or
            getattr(profile, 'role', None) == 'field_agent'):
        return HttpResponseForbidden("Access Denied")

    from .forms import CreateFarmerForm

    if request.method == "POST":
        form = CreateFarmerForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            password = cd.get("password") or _generate_password()

            farmer = Farmer.objects.create_user(
                username=cd["username"],
                email=cd.get("email", ""),
                password=password,
                first_name=cd.get("first_name", ""),
                last_name=cd.get("last_name", ""),
                phone_number=cd.get("phone_number", ""),
            )

            # The post_save signal already created the UserProfile,
            # so we just update role and leave is_approved=False
            farmer_profile = farmer.profile
            farmer_profile.role = "farmer"
            farmer_profile.is_approved = False
            farmer_profile.save()

            if cd.get("password"):
                messages.success(
                    request,
                    f"Farmer '{farmer.username}' created successfully. "
                    "Awaiting admin approval."
                )
            else:
                messages.success(
                    request,
                    f"Farmer '{farmer.username}' created successfully with "
                    f"auto-generated password: {password}. "
                    "Awaiting admin approval."
                )
            return redirect("agent_dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
            # Re-render the agent dashboard with the invalid form
            from .forms import FarmActivityForm
            recent_farmers = Farmer.objects.filter(
                profile__role='farmer'
            ).order_by('-registration_date')[:10]
            recent_activities = FarmActivity.objects.filter(
                created_by=request.user
            ).order_by('-date')[:10]
            return render(request, "Farmers/agent_dashboard.html", {
                "farmer_form": form,
                "activity_form": FarmActivityForm(),
                "recent_farmers": recent_farmers,
                "recent_activities": recent_activities,
            })

    return redirect("agent_dashboard")


@login_required
def create_farm_activity(request):
    """Field agent records a farm activity."""
    profile = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or
            getattr(profile, 'role', None) == 'field_agent'):
        return HttpResponseForbidden("Access Denied")

    from .forms import FarmActivityForm

    if request.method == "POST":
        form = FarmActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user
            activity.save()
            messages.success(request, "Farm activity recorded successfully.")
            return redirect("agent_dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
            from .forms import CreateFarmerForm
            recent_farmers = Farmer.objects.filter(
                profile__role='farmer'
            ).order_by('-registration_date')[:10]
            recent_activities = FarmActivity.objects.filter(
                created_by=request.user
            ).order_by('-date')[:10]
            return render(request, "Farmers/agent_dashboard.html", {
                "farmer_form": CreateFarmerForm(),
                "activity_form": form,
                "recent_farmers": recent_farmers,
                "recent_activities": recent_activities,
            })

    return redirect("agent_dashboard")


def _generate_password(length=12):
    """Generate a random secure password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@login_required
def partner_dashboard(request):
    if not (request.user.is_superuser or
            getattr(getattr(request.user, 'profile', None), 'role', None) == 'investor'):
        return HttpResponseForbidden("Access Denied")

    from django.db.models import Sum
    from .models import Investment, Announcement as Ann

    investments = Investment.objects.filter(
        investor=request.user
    ).select_related("farm").order_by("-invested_at")
    total_invested = investments.aggregate(total=Sum("amount"))["total"] or 0
    announcements = Ann.objects.filter(is_active=True).order_by("-created_at")[:10]

    return render(request, "Farmers/partner_dashboard.html", {
        "investments": investments,
        "total_invested": total_invested,
        "announcements": announcements,
    })

