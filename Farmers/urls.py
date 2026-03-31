from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FarmerRegistrationView,
    AnnouncementViewSet,
    MessageViewSet,
    farmer_dashboard,
    agent_dashboard,
    partner_dashboard,
    farmer_set_password,
)

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('register/', FarmerRegistrationView.as_view(), name='farmer-register'),

    # Dashboards
    path('farmer/dashboard/', farmer_dashboard, name='farmer_dashboard'),
    path('agent/dashboard/', agent_dashboard, name='agent_dashboard'),
    path('partner/dashboard/', partner_dashboard, name='partner_dashboard'),

    # Password setup (token-based, no login required)
    path(
        'farmer/set-password/<uidb64>/<token>/',
        farmer_set_password,
        name='farmer_set_password',
    ),

    # API routes
    path('', include(router.urls)),
]
