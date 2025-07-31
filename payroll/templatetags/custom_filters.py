# myapp/templatetags/custom_filters.py
from django import template
register = template.Library()
@register.filter(name="round2")
def round2(value):
    try:
        return int(round(float(value)))  # Round and cast to int
    except (ValueError, TypeError):
        return value