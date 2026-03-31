from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from Farmers.views import home, CustomLoginView, CustomLogoutView

urlpatterns = [
    path('', home, name='home'),

    # Auth at root level
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Password reset flow (used for farmer password-setup after approval)
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(success_url='/login/'),
        name='password_reset_confirm',
    ),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Admin
    path('admin/', admin.site.urls),

    # Farmer app routes (dashboards + API)
    path('api/farmers/', include('Farmers.urls')),
]
