from django.conf import settings


def site_settings(request):
    user = getattr(request, 'user', None)
    is_admin = bool(
        user and user.is_authenticated and (
            user.is_superuser or user.groups.filter(name=settings.ADMIN_GROUP_NAME).exists()
        )
    )
    return {
        'HOSPITAL_NAME': settings.HOSPITAL_NAME,
        'CURRENCY': settings.CURRENCY_SYMBOL,
        'is_admin': is_admin,
    }
