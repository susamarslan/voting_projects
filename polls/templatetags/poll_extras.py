from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def relative_time(value):
    """'az önce', '3 saat önce', '2 gün önce' gibi tek birimli göreli zaman."""
    if not value:
        return ""
    if timezone.now() - value < timedelta(minutes=1):
        return "az önce"
    return f"{timesince(value, depth=1)} önce"
