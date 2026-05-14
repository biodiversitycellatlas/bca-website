"""Custom static files storage backend for Django."""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class JSModuleManifestStorage(ManifestStaticFilesStorage):
    # Rewrite JavaScript module imports for static files with hashed filenames
    support_js_module_import_aggregation = True
