from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from Farmers.views import home, CustomLoginView, CustomLogoutView

urlpatterns = [
    path('', home, name='home'),

    # Auth at root level
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Password reset / setup (used after admin approval email)
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='Farmers/password_reset_confirm.html',
            success_url='/reset/done/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='Farmers/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),

    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/farmers/', include('Farmers.urls')),
]
