from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Message
from .serializers import MessageSerializer
from Farmers.decorators import approved_user_required
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Sum

from .models import Farmer, UserProfile, Farm, Harvest, Investment, FarmActivity, Announcement
from .forms import FarmerCreateByAgentForm
from .serializers import (
    FarmerSerializer,
    FarmSerializer,
    HarvestSerializer,
    InvestmentSerializer,
    FarmActivitySerializer,
    AnnouncementSerializer,
    FarmerRegistrationSerializer,
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
        return Farmer.objects.filter(id=user.id)

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
        return Farm.objects.none()

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
        elif user.role in ['investor', 'farmer']:
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
    permission_classes = []


# -------------------------------
# Announcements ViewSet (read-only)
# -------------------------------
class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Announcement.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = AnnouncementSerializer


# -------------------------------
# Message ViewSet
# -------------------------------
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


# -------------------------------
# General dashboard (API-protected)
# -------------------------------
@approved_user_required
def dashboard(request):
    return render(request, "Farmers/dashboard.html")


# -------------------------------
# Public home
# -------------------------------
def home(request):
    return render(request, "Farmers/home.html")


# -------------------------------
# Unified login
# -------------------------------
class CustomLoginView(LoginView):
    template_name = "Farmers/login.html"

    def form_valid(self, form):
        user = form.get_user()
        profile, _ = UserProfile.objects.get_or_create(user=user)

        if not user.is_superuser and not profile.is_approved:
            messages.error(
                self.request,
                "Your account is pending admin approval. "
                "You will receive an email when your account is activated.",
            )
            return redirect('login')

        return super().form_valid(form)

    def form_invalid(self, form):
        """Provide specific guidance when a farmer is unapproved or has no password yet."""
        username = self.request.POST.get("username", "").strip()
        if username:
            try:
                user = Farmer.objects.get(username=username)
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if not profile.is_approved:
                    messages.error(
                        self.request,
                        "Your account is pending admin approval. "
                        "You will receive an email when your account is activated.",
                    )
                elif not user.has_usable_password():
                    messages.error(
                        self.request,
                        "Your account has been approved. "
                        "Please check your email for a link to set your password before logging in.",
                    )
            except Farmer.DoesNotExist:
                pass
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)

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


# -------------------------------
# Farmer dashboard
# -------------------------------
@login_required
def farmer_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role != 'farmer':
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/farmer_dashboard.html", {"profile": profile})


# -------------------------------
# Field agent dashboard
# -------------------------------
@login_required
def agent_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role != 'field_agent':
        return HttpResponseForbidden("Access Denied")

    form = FarmerCreateByAgentForm()

    if request.method == "POST":
        form = FarmerCreateByAgentForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]

            farmer = Farmer(username=username, email=email)
            farmer.set_unusable_password()
            farmer.save()

            # The post_save signal on Farmer auto-creates a UserProfile with default
            # role='farmer' and is_approved=False. We update explicitly here to
            # guarantee the correct values even if defaults change in the future.
            farmer_profile = UserProfile.objects.get(user=farmer)
            farmer_profile.role = "farmer"
            farmer_profile.is_approved = False
            farmer_profile.save()

            messages.success(
                request,
                f"Farmer '{username}' registered successfully. "
                "Their account is pending admin approval.",
            )
            return redirect("agent_dashboard")

    pending_farmers = (
        UserProfile.objects
        .filter(role="farmer", is_approved=False)
        .select_related("user")
        .order_by("-user__registration_date")
    )

    return render(request, "Farmers/agent_dashboard.html", {
        "form": form,
        "pending_farmers": pending_farmers,
    })


# -------------------------------
# Investor / partner dashboard
# -------------------------------
@login_required
def partner_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role != 'investor':
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
        "profile": profile,
        "investments": investments,
        "total_invested": total_invested,
        "announcements": announcements,
    })
