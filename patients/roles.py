from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def in_group(user, *group_names):
    return user.is_authenticated and user.groups.filter(name__in=group_names).exists()


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or in_group(user, settings.ADMIN_GROUP_NAME))


def is_pharmacist(user):
    return is_admin(user) or in_group(user, settings.PHARMACIST_GROUP_NAME)


def get_doctor(user):
    """Return the Doctor profile linked to this user, or None."""
    if not user.is_authenticated:
        return None
    if not hasattr(user, '_doctor_profile'):
        from .models import Doctor
        user._doctor_profile = Doctor.objects.filter(user=user).first()
    return user._doctor_profile


def role_required(check, message="You don't have permission to access this page."):
    """Allow access only when check(user) is truthy."""
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if check(request.user):
                return func(request, *args, **kwargs)
            messages.error(request, message)
            return redirect('patients:dashboard')
        return wrapper
    return decorator


admin_required = role_required(is_admin)
pharmacist_required = role_required(is_pharmacist)
doctor_or_admin_required = role_required(
    lambda user: is_admin(user) or get_doctor(user) is not None,
    "Only doctors can access this page.",
)
