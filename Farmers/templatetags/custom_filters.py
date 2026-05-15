from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    Usage in template: {{ mydict|get_item:mykey }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return ""
