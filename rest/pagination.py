from rest_framework.pagination import LimitOffsetPagination

class StandardPagination(LimitOffsetPagination):
    """ Custom pagination. """
    default_limit = 10
    max_limit = 100

    def get_limit(self, request):
        # Fetch all records if limit=0
        if request.query_params.get('limit') == '0':
            return None
        return super().get_limit(request)
