from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os

from Farmers.views import home, app_download, CustomLoginView, CustomLogoutView, request_password_reset_from_admin, page_not_found, service_worker

handler404 = 'Farmers.views.page_not_found'

urlpatterns = [
    path('', home, name='home'),
    path('app-download/', app_download, name='app_download'),
    path('sw.js', service_worker, name='service_worker'),

    # Auth at root level
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Password reset (used after admin approval)
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='Farmers/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='Farmers/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='Farmers/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='Farmers/password_reset_complete.html'), name='password_reset_complete'),
    path('request-password-link/', request_password_reset_from_admin, name='request_password_reset_from_admin'),

    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/farmers/', include('Farmers.urls')),
]

if settings.DEBUG:
    _farmers_images_root = os.path.join(settings.BASE_DIR, 'Farmers', 'Images')
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'Farmers', 'static'))
    urlpatterns += [
        path('Farmers/Images/<path:path>', serve, {'document_root': _farmers_images_root}),
    ]
