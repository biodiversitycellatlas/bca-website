from django.contrib import admin
from django.urls import include, path, reverse
from django.shortcuts import redirect

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path('', include('app.urls')),
    path('admin/', admin.site.urls, name='admin'),

    # Blog URLs
    path('blog/', include(wagtail_urls)),
    path('wagtail/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),

    # REST URLs
    path('api/v1/', include('rest.urls')),
    path('api/', lambda request: redirect(reverse('rest:index'), permanent=False), name='api'),
]
