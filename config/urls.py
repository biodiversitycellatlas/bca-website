from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('web_app.urls')),
    path('api/v1/', include('rest.urls')),
    path('admin/', admin.site.urls),
]
