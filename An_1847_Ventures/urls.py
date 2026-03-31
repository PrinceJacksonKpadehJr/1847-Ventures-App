from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from Farmers.views import home, CustomLoginView, CustomLogoutView

urlpatterns = [
    path('', home, name='home'),

    # Auth at root level
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Password reset (used after admin approval)
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='Farmers/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='Farmers/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='Farmers/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='Farmers/password_reset_complete.html'), name='password_reset_complete'),

    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/farmers/', include('Farmers.urls')),
]
