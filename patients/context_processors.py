from django.conf import settings

from .roles import get_doctor, is_admin, is_pharmacist


def site_settings(request):
    user = getattr(request, 'user', None)
    authenticated = bool(user and user.is_authenticated)
    return {
        'HOSPITAL_NAME': settings.HOSPITAL_NAME,
        'CURRENCY': settings.CURRENCY_SYMBOL,
        'is_admin': authenticated and is_admin(user),
        'is_pharmacist': authenticated and is_pharmacist(user),
        'current_doctor': get_doctor(user) if authenticated else None,
    }
