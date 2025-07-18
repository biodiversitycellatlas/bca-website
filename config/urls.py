from django.urls import include, path, reverse
from django.shortcuts import redirect
from django.conf import settings

urlpatterns = [
    path('', include('app.urls')),
    path('api/v1/', include('rest.urls')),
    path('api/', lambda request: redirect(reverse('rest:index'), permanent=False), name='api'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
