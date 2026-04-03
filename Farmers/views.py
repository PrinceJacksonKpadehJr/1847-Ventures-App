from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from Farmers.decorators import approved_user_required
from Farmers.models import UserProfile, FarmReport
from .forms import FarmerCreateByAgentForm, FarmReportForm
from .models import Farmer, Farm, Harvest, Investment, FarmActivity, Announcement, Message
from .serializers import (
    FarmerSerializer,
    FarmSerializer,
    HarvestSerializer,
    InvestmentSerializer,
    FarmActivitySerializer,
    AnnouncementSerializer,
    FarmerRegistrationSerializer,
    MessageSerializer,
)


# ===== Field Agent Required Decorator =====
def field_agent_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if request.user.is_superuser or profile.role == "field_agent":
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access denied: Only field agents allowed.")
    return wrapped


# -------------------------------
# Farmer ViewSet
# -------------------------------
class FarmerViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role == 'admin':
            return Farmer.objects.all()
        elif profile.role == 'field_agent':
            return Farmer.objects.filter(profile__role='farmer')
        return Farmer.objects.filter(id=user.id)

    def perform_create(self, serializer):
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role in ['admin', 'field_agent']:
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
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role == 'admin':
            return Farm.objects.all()
        elif profile.role == 'field_agent':
            return Farm.objects.all()
        elif profile.role == 'farmer':
            return Farm.objects.filter(owner=user)
        return Farm.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role in ['admin', 'field_agent']:
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
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role == 'admin':
            return Harvest.objects.all()
        elif profile.role in ['field_agent', 'investor']:
            return Harvest.objects.all()
        elif profile.role == 'farmer':
            return Harvest.objects.filter(farm__owner=user)
        return Harvest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role in ['admin', 'field_agent', 'farmer']:
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
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role == 'admin':
            return Investment.objects.all()
        elif profile.role == 'investor':
            return Investment.objects.filter(investor=user)
        elif profile.role == 'farmer':
            return Investment.objects.filter(investor=user)
        return Investment.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role in ['admin', 'investor']:
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
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role == 'admin':
            return FarmActivity.objects.all()
        elif profile.role in ['field_agent', 'investor']:
            return FarmActivity.objects.all()
        elif profile.role == 'farmer':
            return FarmActivity.objects.filter(farmer=user)
        return FarmActivity.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.is_superuser or profile.role in ['admin', 'field_agent', 'farmer']:
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
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.role in ['field_agent', 'farmer']:
            return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)
        return Message.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        receiver = serializer.validated_data['receiver']
        profile, _ = UserProfile.objects.get_or_create(user=user)
        receiver_profile, _ = UserProfile.objects.get_or_create(user=receiver)

        if profile.role == 'farmer' and receiver.is_superuser:
            raise PermissionDenied("Farmers cannot message admin.")
        if profile.role == 'farmer' and receiver_profile.role != 'field_agent':
            raise PermissionDenied("Farmers can only message field agents.")

        serializer.save(sender=user)


@approved_user_required
def dashboard(request):
    return render(request, "Farmers/dashboard.html")


def home(request):
    return render(request, "Farmers/home.html")


class CustomLoginView(LoginView):
    template_name = "Farmers/login.html"

    def form_valid(self, form):
        user = form.get_user()

        if not user.is_active:
            messages.error(self.request, "Your account is inactive. Contact an admin.")
            return redirect('login')

        # Ensure profile exists
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Block unapproved users (except superuser)
        if not user.is_superuser and not profile.is_approved:
            messages.error(self.request, "Your account is not yet approved.")
            return redirect('login')

        return super().form_valid(form)

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


@login_required
def farmer_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not request.user.is_superuser and profile.role != 'farmer':
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/farmer_dashboard.html")


UserModel = get_user_model()


@field_agent_required
def agent_dashboard(request):
    farmer_form = FarmerCreateByAgentForm()
    report_form = FarmReportForm()
    farmers_qs = UserModel.objects.filter(profile__role="farmer")
    recent_farmers = UserProfile.objects.filter(role="farmer").order_by('-id')[:5]
    recent_reports = FarmReport.objects.order_by('-created_at')[:5]

    if request.method == "POST":
        if 'create_farmer' in request.POST:
            farmer_form = FarmerCreateByAgentForm(request.POST)
            if farmer_form.is_valid():
                username = farmer_form.cleaned_data['username']
                email = farmer_form.cleaned_data['email']
                farmer = UserModel.objects.create(username=username)
                farmer.set_unusable_password()
                farmer.save()
                profile, _ = UserProfile.objects.get_or_create(user=farmer)
                profile.role = "farmer"
                profile.is_approved = False
                profile.email = email
                profile.save()
                messages.success(request, f"Farmer '{username}' registered and pending admin approval.")
                return redirect('agent_dashboard')
            else:
                messages.error(request, "Please fix the errors in the farmer registration form.")

        elif 'create_report' in request.POST:
            report_form = FarmReportForm(request.POST)
            report_form.fields['farmer'].queryset = farmers_qs
            if report_form.is_valid():
                report = report_form.save(commit=False)
                report.field_agent = request.user
                report.save()
                messages.success(request, "Farm report successfully submitted.")
                return redirect('agent_dashboard')
            else:
                messages.error(request, "Please fix the errors in the farm report form.")

    report_form.fields['farmer'].queryset = farmers_qs

    context = {
        'farmer_form': farmer_form,
        'report_form': report_form,
        'recent_farmers': recent_farmers,
        'recent_reports': recent_reports,
    }
    return render(request, 'Farmers/agent_dashboard.html', context)


@login_required
def partner_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not request.user.is_superuser and profile.role != 'investor':
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
