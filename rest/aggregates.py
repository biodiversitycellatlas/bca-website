from django.db.models import Aggregate, FloatField

class Median(Aggregate):
    ''' Calculate median using native PostgreSQL PERCENTILE_CONT. '''
    function = 'PERCENTILE_CONT'
    name = 'median'
    output_field = FloatField()
    template = '%(function)s(0.5) WITHIN GROUP (ORDER BY %(expressions)s)'

class PercentileCont(Aggregate):
    ''' Calculate percentiles using PERCENTILE_CONT. '''
    function = 'PERCENTILE_CONT'
    name = 'PercentileCont'
    output_field = FloatField()
    template = '%(function)s (%(percentile)s) WITHIN GROUP (ORDER BY %(expressions)s)'