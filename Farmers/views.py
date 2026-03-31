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
from Farmers.models import UserProfile
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from .models import Farmer, Farm, Crop, Harvest, Investment, FarmActivity, Announcement
from .serializers import (
    FarmerSerializer,
    FarmSerializer,
    HarvestSerializer,
    InvestmentSerializer,
    FarmActivitySerializer,
    AnnouncementSerializer,
    FarmerRegistrationSerializer,
)
from .forms import FarmerRegistrationForm, FarmActivityForm


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
    queryset = Announcement.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = AnnouncementSerializer


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Message.objects.all()

        if hasattr(user, 'profile') and user.profile.role in ['field_agent', 'farmer']:
            return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)

        return Message.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        receiver = serializer.validated_data['receiver']

        if hasattr(user, 'profile') and user.profile.role == 'farmer' and receiver.is_superuser:
            raise PermissionDenied("Farmers cannot message admin.")

        if hasattr(user, 'profile') and user.profile.role == 'farmer':
            receiver_role = getattr(getattr(receiver, 'profile', None), 'role', None)
            if receiver_role != 'field_agent':
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
    profile = getattr(request.user, 'profile', None)
    if profile is None or profile.role != 'farmer':
        return HttpResponseForbidden("Access Denied")

    # Show unread messages (includes password-setup prompt from admin)
    unread_messages = Message.objects.filter(
        receiver=request.user, is_read=False
    ).order_by('-created_at')

    return render(request, "Farmers/farmer_dashboard.html", {
        "unread_messages": unread_messages,
    })


@login_required
def agent_dashboard(request):
    profile = getattr(request.user, 'profile', None)
    if profile is None or profile.role != 'field_agent':
        return HttpResponseForbidden("Access Denied")

    registration_form = FarmerRegistrationForm()
    activity_form = FarmActivityForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'register_farmer':
            registration_form = FarmerRegistrationForm(request.POST)
            if registration_form.is_valid():
                farmer = Farmer(
                    username=registration_form.cleaned_data['username'],
                    first_name=registration_form.cleaned_data.get('first_name', ''),
                    last_name=registration_form.cleaned_data.get('last_name', ''),
                    email=registration_form.cleaned_data.get('email', '') or '',
                    phone_number=registration_form.cleaned_data.get('phone_number', '') or '',
                )
                farmer.set_unusable_password()
                farmer.save()
                # UserProfile auto-created by post_save signal with role='farmer',
                # is_approved=False
                messages.success(
                    request,
                    f"Farmer '{farmer.username}' registered successfully. "
                    "Awaiting admin approval.",
                )
                return redirect('agent_dashboard')

        elif action == 'log_activity':
            activity_form = FarmActivityForm(request.POST)
            if activity_form.is_valid():
                farmer = activity_form.cleaned_data['farmer']
                farm = Farm.objects.create(
                    name=activity_form.cleaned_data['farm_name'],
                    owner=farmer,
                    location=activity_form.cleaned_data['location'],
                    size_in_hectares=activity_form.cleaned_data['size_in_hectares'],
                )
                Crop.objects.create(
                    farm=farm,
                    name=activity_form.cleaned_data['crop_name'],
                    planting_date=activity_form.cleaned_data['date_planted'],
                    harvest_date=activity_form.cleaned_data['approx_harvest_date'],
                    expected_yield_kg=activity_form.cleaned_data['expected_yield_kg'],
                    seeds_planted_kg=activity_form.cleaned_data['seeds_planted_kg'],
                )
                messages.success(
                    request,
                    f"Farm activity logged for '{farmer.username}'.",
                )
                return redirect('agent_dashboard')

    registered_farmers = (
        Farmer.objects.filter(profile__role='farmer')
        .select_related('profile')
        .order_by('-registration_date')
    )
    farm_activities = (
        Farm.objects.select_related('owner')
        .prefetch_related('crops')
        .order_by('-created_at')
    )

    return render(request, "Farmers/agent_dashboard.html", {
        'registration_form': registration_form,
        'activity_form': activity_form,
        'registered_farmers': registered_farmers,
        'farm_activities': farm_activities,
    })


@login_required
def partner_dashboard(request):
    profile = getattr(request.user, 'profile', None)
    if profile is None or profile.role != 'investor':
        return HttpResponseForbidden("Access Denied")

    from django.db.models import Sum
    investments = (
        Investment.objects.filter(investor=request.user)
        .select_related('farm')
        .order_by('-invested_at')
    )
    total_invested = investments.aggregate(total=Sum('amount'))['total'] or 0
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:10]

    return render(request, "Farmers/partner_dashboard.html", {
        'investments': investments,
        'total_invested': total_invested,
        'announcements': announcements,
    })


def farmer_set_password(request, uidb64, token):
    """
    Allow a farmer to set their password using a one-time token link
    generated when their account is approved by an admin.
    This view does NOT require the farmer to be logged in.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        farmer = Farmer.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Farmer.DoesNotExist):
        farmer = None

    if farmer is None or not default_token_generator.check_token(farmer, token):
        messages.error(
            request,
            "This password setup link is invalid or has already been used. "
            "Please contact your field agent or admin.",
        )
        return redirect('login')

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        ctx = {'uidb64': uidb64, 'token': token, 'username': farmer.username}

        if not password1:
            messages.error(request, "Password cannot be empty.")
            return render(request, 'Farmers/set_password.html', ctx)

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'Farmers/set_password.html', ctx)

        # Use Django's built-in password validators (length, common, similarity)
        try:
            validate_password(password1, user=farmer)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, 'Farmers/set_password.html', ctx)

        farmer.set_password(password1)
        farmer.save()
        messages.success(
            request,
            "Password set successfully! You can now log in with your username and password.",
        )
        return redirect('login')

    return render(request, 'Farmers/set_password.html', {
        'uidb64': uidb64,
        'token': token,
        'username': farmer.username,
    })
