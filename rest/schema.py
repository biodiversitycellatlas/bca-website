from drf_spectacular.plumbing import get_relative_url, set_query_parameters
from drf_spectacular.settings import spectacular_settings
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import AUTHENTICATION_CLASSES
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


class SpectacularElementsView(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    permission_classes = spectacular_settings.SERVE_PERMISSIONS
    authentication_classes = AUTHENTICATION_CLASSES
    url_name = "rest:schema"
    url = None
    template_name = "rest/elements.html"
    title = spectacular_settings.TITLE

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        return Response(
            data={
                "title": self.title,
                "js_dist": "https://unpkg.com/@stoplight/elements/web-components.min.js",
                "css_dist": "https://unpkg.com/@stoplight/elements/styles.min.css",
                "schema_url": self._get_schema_url(request),
            },
            template_name=self.template_name,
        )

    def _get_schema_url(self, request):
        schema_url = self.url or get_relative_url(
            reverse(self.url_name, request=request)
        )
        return set_query_parameters(
            url=schema_url,
            lang=request.GET.get("lang"),
            version=request.GET.get("version"),
        )
