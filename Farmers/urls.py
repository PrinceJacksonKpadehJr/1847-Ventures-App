from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UnifiedLoginView
from django.urls import path
from .views import agent_dashboard
from .views import (
    FarmerRegistrationView,
    AnnouncementViewSet,
    MessageViewSet,
    farmer_dashboard,
    agent_dashboard,
    partner_dashboard,
        admin_dashboard,
    create_user,
    assign_farmer_request,
    review_farmer,
    approve_farmer,
    reject_farmer,
    request_more_info,
    mark_notification_read,
)

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('register/', FarmerRegistrationView.as_view(), name='farmer-register'),

    # Login
    path("login/", UnifiedLoginView.as_view(), name="login"),

    # Dashboards
    path('farmer/dashboard/', farmer_dashboard, name='farmer_dashboard'),
    path('agent/dashboard/', agent_dashboard, name='agent_dashboard'),
    path('partner/dashboard/', partner_dashboard, name='partner_dashboard'),

    # API routes
    path('', include(router.urls)),
]
from django.urls import path
from .views import UnifiedLoginView, farmer_dashboard, agent_dashboard, partner_dashboard

urlpatterns = [
    path("login/", UnifiedLoginView.as_view(), name="login"),

    path("farmer/dashboard/", farmer_dashboard, name="farmer_dashboard"),
    path("agent/dashboard/", agent_dashboard, name="agent_dashboard"),
    path("partner/dashboard/", partner_dashboard, name="partner_dashboard"),
]

urlpatterns = [
    path('agent/dashboard/', agent_dashboard, name='agent_dashboard'),
    # ... add other URLs here
]