from django import template

register = template.Library()


@register.filter
def split(value, delimiter=","):
    return value.split(delimiter)


@register.filter
def get_file_type(queryset, key):
    return queryset.filter(type=key).first()
