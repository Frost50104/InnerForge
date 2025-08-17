from django import template

register = template.Library()

@register.filter
def mmss(seconds: int) -> str:
    try:
        s = int(seconds or 0)
    except (TypeError, ValueError):
        s = 0
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}"
