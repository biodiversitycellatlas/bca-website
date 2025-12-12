"""Cache functions."""

from django.core.cache import cache

def get_validated_cache(key, validation):
    """Get cache for a given key and check validation string."""
    cached = cache.get(key)
    if cached is not None:
        data, cached_validation = cached
        if validation == cached_validation:
            return data
    return None

def set_validated_cache(key, validation, data, timeout=24 * 60 * 60):
    """Set cache for a given key with a validation string."""
    cache.set(key, (data, validation), timeout=timeout)
