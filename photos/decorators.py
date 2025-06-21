from django.conf import settings
from django.contrib.auth.decorators import user_passes_test


def is_moderator(user):
    return user.is_authenticated and (user.is_superuser or user.id in getattr(settings, "MODERATOR_IDS", []))

moderator_required = user_passes_test(is_moderator)
