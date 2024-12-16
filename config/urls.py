from django.contrib import admin
from django.urls import include, path, reverse
from django.shortcuts import redirect

urlpatterns = [
    path('', include('web_app.urls')),
    path('api/v1/', include('rest.urls')),
    path('api/', lambda request: redirect(reverse('rest:elements'), permanent=False), name='api'),
    path('admin/', admin.site.urls, name='admin'),
]
