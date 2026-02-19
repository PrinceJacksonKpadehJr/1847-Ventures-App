from django.contrib import admin
from django.urls import path, include
from Farmers.views import home, CustomLoginView, CustomLogoutView

urlpatterns = [
    path('', home, name='home'),

    # Auth at root level
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/farmers/', include('Farmers.urls')),
]
