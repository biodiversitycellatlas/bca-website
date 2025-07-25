from django.db.models import CharField, Func, IntegerField, Value


class ArrayToString(Func):
    """
    Concatenate array field into string using a given delimiter.

    Args:
        expression (Field): The database column containing the array field.
        delimiter (str): The delimiter used to join array elements (default: ',').

    Returns:
        str: The concatenated elements of the array.

    Example:
        Gene.objects.annotate(ArrayToString('domains')
        Gene.objects.annotate(ArrayToString('domains', delimiter=';'))
    """

    function = "array_to_string"
    output_field = CharField()
    default_alias = "concatenated"
    template = "%(function)s(%(expressions)s, '%(delimiter)s')"

    def __init__(self, expression, **extra):
        # Default to comma
        extra["delimiter"] = extra.get("delimiter", ",")
        super().__init__(expression, **extra)


class ArrayPosition(Func):
    """
    Find index of the first occurrence of an element in a given array.

    Args:
        expression (Field): The database column.
        array (list): The (one-dimensional) Python list.

    Returns:
        int: The index of the elements relative to the array.

    Example:
        # Annotate index
        Gene.objects.annotate(ArrayPosition('name', array=['Tadh_P1002', 'Tadh_P1068']))

        # Order based on array position
        Gene.objects.order_by(ArrayPosition('name', array=['Tadh_P1002', 'Tadh_P1068']))
    """

    function = "array_position"
    output_field = IntegerField()
    default_alias = "index"
    template = "%(function)s(ARRAY%(array)s, %(expressions)s)"


class Correlation(Func):
    function = "CORR"
    template = "%(function)s(%(expressions)s)"
