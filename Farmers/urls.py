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

    # Dashboards
    path('farmer/dashboard/', farmer_dashboard, name='farmer_dashboard'),
    path('agent/dashboard/', agent_dashboard, name='agent_dashboard'),
    path('partner/dashboard/', partner_dashboard, name='partner_dashboard'),
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),

    # Field agent actions
    path('agent/create-farmer/', create_farmer, name='create_farmer'),

    # Admin actions
    path('admin/create-user/', create_user, name='create_user'),
    path('admin/assign-farmer/', assign_farmer_request, name='assign_farmer_request'),
    path('admin/review-farmer/<int:farmer_id>/', review_farmer, name='review_farmer'),
    path('admin/approve-farmer/<int:farmer_id>/', approve_farmer, name='approve_farmer'),
    path('admin/reject-farmer/<int:farmer_id>/', reject_farmer, name='reject_farmer'),
    path('admin/request-info/<int:farmer_id>/', request_more_info, name='request_more_info'),
    path('admin/notification/<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),

    # API routes
    path('', include(router.urls)),
]
