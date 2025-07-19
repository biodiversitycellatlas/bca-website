from django.db.models import Func, IntegerField


class RowNumber(Func):
    function = "ROW_NUMBER"
    template = "%(function)s() OVER ()"
    output_field = IntegerField()
