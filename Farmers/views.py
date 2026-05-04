from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from .models import Message
from .serializers import MessageSerializer
from Farmers.decorators import approved_user_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from Farmers.models import UserProfile, AdminNotification, FarmerRegistrationRequest
from django.contrib import messages
from .forms import FarmerCreateByAgentForm, CreateUserForm, FarmerRegistrationRequestForm







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

        if role == 'admin':
            return reverse_lazy('admin_dashboard')

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
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'farmer':
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/farmer_dashboard.html")


@login_required
def agent_dashboard(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'field_agent':
        return HttpResponseForbidden("Access Denied")
    farmers = Farmer.objects.filter(profile__role='farmer').order_by('-registration_date')
    pending_requests = FarmerRegistrationRequest.objects.filter(
        assigned_agent=request.user, status='pending'
    )
    return render(request, "Farmers/agent_dashboard.html", {
        "farmers": farmers,
        "pending_requests": pending_requests,
    })


@login_required
def create_farmer(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'field_agent':
        return HttpResponseForbidden("Access Denied")

    if request.method == "POST":
        form = FarmerCreateByAgentForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            farmer = Farmer(username=username, email=email)
            farmer.set_unusable_password()
            farmer.save()
            profile = farmer.profile
            profile.role = "farmer"
            profile.is_approved = False
            profile.created_by_agent = request.user
            profile.save()

            # Mark registration request as completed if one was linked
            request_id = request.POST.get("request_id")
            if request_id:
                try:
                    reg_request = FarmerRegistrationRequest.objects.get(
                        pk=request_id, assigned_agent=request.user, status='pending'
                    )
                    reg_request.status = 'completed'
                    reg_request.save()
                except FarmerRegistrationRequest.DoesNotExist:
                    pass

            # Notify all admins
            admin_users = Farmer.objects.filter(profile__role='admin', is_active=True)
            for admin_user in admin_users:
                AdminNotification.objects.create(
                    recipient=admin_user,
                    notification_type='new_farmer',
                    message=(
                        f"Field agent '{request.user.username}' has registered a new farmer: "
                        f"'{username}' ({email}). Pending your approval."
                    ),
                    related_farmer=farmer,
                )

            messages.success(
                request,
                f"Farmer '{username}' has been registered and is pending admin approval."
            )
            return redirect("agent_dashboard")
    else:
        form = FarmerCreateByAgentForm()

    request_id = request.GET.get("request_id", "")
    return render(request, "Farmers/create_farmer.html", {"form": form, "request_id": request_id})


@login_required
def partner_dashboard(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'investor':
        return HttpResponseForbidden("Access Denied")
    return render(request, "Farmers/partner_dashboard.html")


# -----------------------------------------------------------------------
# Admin Dashboard
# -----------------------------------------------------------------------
def _require_admin(request):
    """Return None if the user is a valid admin, otherwise an HttpResponseForbidden."""
    if not request.user.is_authenticated:
        return redirect('login')
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return HttpResponseForbidden("Access Denied")
    return None


@login_required
def admin_dashboard(request):
    denied = _require_admin(request)
    if denied:
        return denied

    pending_farmers = Farmer.objects.filter(
        profile__role='farmer', profile__is_approved=False, is_active=True
    ).order_by('-registration_date')

    notifications = AdminNotification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]

    unread_count = AdminNotification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    stats = {
        'total_farmers': Farmer.objects.filter(profile__role='farmer').count(),
        'pending_approvals': pending_farmers.count(),
        'total_agents': Farmer.objects.filter(profile__role='field_agent').count(),
        'total_partners': Farmer.objects.filter(profile__role='investor').count(),
        'total_admins': Farmer.objects.filter(profile__role='admin').count(),
    }

    return render(request, "Farmers/admin_dashboard.html", {
        "pending_farmers": pending_farmers,
        "notifications": notifications,
        "unread_count": unread_count,
        "stats": stats,
    })


@login_required
def create_user(request):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            role = form.cleaned_data["role"]
            first_name = form.cleaned_data.get("first_name", "")
            last_name = form.cleaned_data.get("last_name", "")

            new_user = Farmer(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            new_user.set_unusable_password()
            new_user.save()

            profile = new_user.profile
            profile.role = role
            profile.is_approved = True
            profile.save()

            role_label = dict(CreateUserForm.ROLE_CHOICES).get(role, role)
            messages.success(
                request,
                f"{role_label} account '{username}' created successfully. "
                "Send the user a password-reset link so they can set their password."
            )
            return redirect("admin_dashboard")
    else:
        role_prefill = request.GET.get("role", "field_agent")
        form = CreateUserForm(initial={"role": role_prefill})

    return render(request, "Farmers/create_user.html", {"form": form})


@login_required
def assign_farmer_request(request):
    denied = _require_admin(request)
    if denied:
        return denied

    if request.method == "POST":
        form = FarmerRegistrationRequestForm(request.POST)
        if form.is_valid():
            FarmerRegistrationRequest.objects.create(
                created_by=request.user,
                assigned_agent=form.cleaned_data["assigned_agent"],
                farmer_name=form.cleaned_data["farmer_name"],
                farmer_email=form.cleaned_data.get("farmer_email", ""),
                farmer_phone=form.cleaned_data.get("farmer_phone", ""),
                notes=form.cleaned_data.get("notes", ""),
            )
            messages.success(
                request,
                f"Farmer registration request assigned to "
                f"'{form.cleaned_data['assigned_agent'].username}' successfully."
            )
            return redirect("admin_dashboard")
    else:
        form = FarmerRegistrationRequestForm()

    return render(request, "Farmers/assign_farmer_request.html", {"form": form})


@login_required
def review_farmer(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')
    return render(request, "Farmers/review_farmer.html", {"farmer": farmer})


@login_required
def approve_farmer(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')
    profile = farmer.profile
    profile.is_approved = True
    profile.save()

    AdminNotification.objects.filter(
        related_farmer=farmer, is_read=False
    ).update(is_read=True)

    messages.success(request, f"Farmer '{farmer.username}' has been approved.")
    return redirect("admin_dashboard")


@login_required
def reject_farmer(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')

    if request.method == "POST":
        reason = request.POST.get("reason", "No reason provided.")
        agent = farmer.profile.created_by_agent
        if agent:
            Message.objects.create(
                sender=request.user,
                receiver=agent,
                content=(
                    f"Farmer registration for '{farmer.username}' ({farmer.email}) "
                    f"has been rejected.\nReason: {reason}"
                ),
            )

        AdminNotification.objects.filter(
            related_farmer=farmer, is_read=False
        ).update(is_read=True)

        farmer.is_active = False
        farmer.save()
        messages.success(request, f"Farmer '{farmer.username}' has been rejected.")
        return redirect("admin_dashboard")

    return render(request, "Farmers/review_farmer.html", {
        "farmer": farmer,
        "action": "reject",
    })


@login_required
def request_more_info(request, farmer_id):
    denied = _require_admin(request)
    if denied:
        return denied

    farmer = get_object_or_404(Farmer, pk=farmer_id, profile__role='farmer')

    if request.method == "POST":
        info_request = request.POST.get("info_request", "").strip()
        if not info_request:
            messages.error(request, "Please describe what additional information is needed.")
            return render(request, "Farmers/review_farmer.html", {
                "farmer": farmer,
                "action": "request_info",
            })

        agent = farmer.profile.created_by_agent
        if agent:
            Message.objects.create(
                sender=request.user,
                receiver=agent,
                content=(
                    f"Additional information is needed for farmer '{farmer.username}' ({farmer.email}).\n\n"
                    f"Details: {info_request}"
                ),
            )
            messages.success(
                request,
                f"Information request sent to field agent '{agent.username}'."
            )
        else:
            messages.warning(
                request,
                "No field agent is linked to this farmer. Could not send request."
            )
        return redirect("admin_dashboard")

    return render(request, "Farmers/review_farmer.html", {
        "farmer": farmer,
        "action": "request_info",
    })


@login_required
def mark_notification_read(request, notification_id):
    denied = _require_admin(request)
    if denied:
        return denied

    notification = get_object_or_404(
        AdminNotification, pk=notification_id, recipient=request.user
    )
    notification.is_read = True
    notification.save()
    return redirect("admin_dashboard")

