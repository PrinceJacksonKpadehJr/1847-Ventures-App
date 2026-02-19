from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from .models import Message
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
    if request.user.role != 'farmer':
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/farmer_dashboard.html")


@login_required
def agent_dashboard(request):
    if request.user.role != 'field_agent':
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/agent_dashboard.html")


@login_required
def partner_dashboard(request):
    if request.user.role != 'partner':
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/partner_dashboard.html")

