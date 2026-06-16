"""Custom static files storage backend for Django."""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class JSModuleManifestStorage(ManifestStaticFilesStorage):
    # Rewrite JavaScript module imports for static files with hashed filenames
    support_js_module_import_aggregation = True
    # Bun code-split bundles create 5+ levels of chunk imports; each level
    # requires one pass to propagate content-hashes upward (default is 5)
    max_post_process_passes = 15
