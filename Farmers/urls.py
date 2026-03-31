from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FarmerRegistrationView,
    AnnouncementViewSet,
    MessageViewSet,
    farmer_dashboard,
    agent_dashboard,
    partner_dashboard,
    create_farmer,
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

    # Field agent actions
    path('agent/create-farmer/', create_farmer, name='create_farmer'),

    # API routes
    path('', include(router.urls)),
]
