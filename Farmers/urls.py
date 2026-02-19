from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FarmerRegistrationView,
    AnnouncementViewSet,
    MessageViewSet,
    farmer_dashboard,
    agent_dashboard,
    partner_dashboard,
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

    # API routes
    path('', include(router.urls)),
]
