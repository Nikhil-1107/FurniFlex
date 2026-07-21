from django import template
from django.contrib.auth.models import User

register = template.Library()

def _get_country(obj):
    country = 'India'
    if obj:
        if isinstance(obj, User):
            user = obj
        else:
            user = getattr(obj, 'user', None)
            
        if user and user.is_authenticated:
            try:
                country = user.profile.country
            except Exception:
                pass
    return country

@register.filter
def convert_currency(value, request_or_user):
    if value is None:
        return ""
        
    country = _get_country(request_or_user)
            
    rates = {
        'India': {'symbol': '₹', 'rate': 1.0},
        'United States': {'symbol': '$', 'rate': 0.012},
        'United Kingdom': {'symbol': '£', 'rate': 0.0094},
        'Europe': {'symbol': '€', 'rate': 0.011},
        'UAE': {'symbol': 'AED ', 'rate': 0.044},
    }
    
    info = rates.get(country, rates['India'])
    try:
        converted_val = float(value) * info['rate']
        return f"{info['symbol']}{converted_val:,.2f}"
    except (ValueError, TypeError):
        return value

@register.filter
def currency_symbol(request_or_user):
    country = _get_country(request_or_user)
    rates = {
        'India': '₹',
        'United States': '$',
        'United Kingdom': '£',
        'Europe': '€',
        'UAE': 'AED ',
    }
    return rates.get(country, '₹')

@register.filter
def currency_rate(request_or_user):
    country = _get_country(request_or_user)
    rates = {
        'India': 1.0,
        'United States': 0.012,
        'United Kingdom': 0.0094,
        'Europe': 0.011,
        'UAE': 0.044,
    }
    return rates.get(country, 1.0)
