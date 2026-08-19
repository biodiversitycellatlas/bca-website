"""
Bioschemas JSON-LD payload builders.

Each ``Bioschema`` subclass builds a plain ``dict`` describing an entity using
a `Bioschemas released profile <https://bioschemas.org/profiles/>`_. These are
serialised into JSON-LD blocks by the ``bioschemas`` template tags.

Building the payloads here makes them easy to unit test and keeps profile
versions in one place. Only released profiles are targeted -- draft profiles
for the protein-domain pages and a nested citation node were tried and
withdrawn; see section 10 of `report-bioschemas.md` for details. Nested nodes
never carry their own ``@context``: :func:`build_root` adds it to the
top-level node only.
"""

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.urls import NoReverseMatch, reverse

# Released profiles this module emits conformance claims for
PROFILES = {
    "DataCatalog": "https://bioschemas.org/profiles/DataCatalog/0.3-RELEASE-2019_07_01",
    "Dataset": "https://bioschemas.org/profiles/Dataset/1.0-RELEASE",
    "Gene": "https://bioschemas.org/profiles/Gene/1.0-RELEASE",
    "Taxon": "https://bioschemas.org/profiles/Taxon/1.0-RELEASE",
    "TaxonName": "https://bioschemas.org/profiles/TaxonName/1.0-RELEASE",
}

# `dct` is needed for the dct:conformsTo profile claim
CONTEXT = ["https://schema.org", {"dct": "http://purl.org/dc/terms/"}]

# Every BCA species entry describes a taxon at species rank
TAXON_RANK = "species"
DWC_TAXON = "http://rs.tdwg.org/dwc/terms/Taxon"

MEASUREMENT_TECHNIQUE = "single-cell RNA sequencing"

BASE_KEYWORDS = [
    "Biodiversity Cell Atlas",
    "single-cell transcriptomics",
    "gene expression",
    "cell types",
]

FORMATS = {
    "json": "application/json",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
}

# Media types for the downloadable file extensions used by the file models
FILE_FORMATS = {
    "fa": "text/x-fasta",
    "faa": "text/x-fasta",
    "fasta": "text/x-fasta",
    "gz": "application/gzip",
    "tsv": "text/tab-separated-values",
    "csv": "text/csv",
    "txt": "text/plain",
}
DEFAULT_FILE_FORMAT = "application/octet-stream"


# --- helpers -----------------------------------------------------------------


def _get_setting(key, default=None):
    """Return a Django setting, falling back to `default` when unset."""
    return getattr(settings, key, default)


def _absolute_url(request, url):
    """Return `url` as an absolute URI, when a request is available."""
    if not url:
        return None
    if request is None:
        return url
    return request.build_absolute_uri(url)


def _current_page_url(request):
    """Return the absolute URI of the page currently being rendered."""
    return request.build_absolute_uri() if request is not None else None


def _drop_empty(value):
    """Recursively drop dict keys and list items with no value."""
    if isinstance(value, dict):
        items = ((key, _drop_empty(val)) for key, val in value.items())
        return {key: val for key, val in items if not _is_empty(val)}
    if isinstance(value, (list, tuple)):
        items = (_drop_empty(val) for val in value)
        return [val for val in items if not _is_empty(val)]
    return value


def _is_empty(value):
    """Return True for values that should be omitted from the payload."""
    if isinstance(value, (bool, int, float)):
        return False
    return value is None or value in ("", [], {})


def _build_node(profile):
    """Start a JSON-LD node claiming conformance to a Bioschemas profile."""
    return {"@type": profile, "dct:conformsTo": {"@type": "CreativeWork", "@id": PROFILES[profile]}}


def _species_meta(species, key):
    """Return a species `Meta` row by key, or None when absent."""
    return species.meta_set.filter(key=key).first()


def _safe_query_url(obj):
    """Return an object's external query URL, tolerating a missing Source."""
    try:
        return obj.query_url
    except ObjectDoesNotExist:
        return None


def _safe_reverse(view, query=None, args=None):
    """Reverse a view name, returning None when the route does not exist."""
    try:
        url = reverse(view, args=args)
    except NoReverseMatch:  # pragma: no cover - defensive
        return None
    return f"{url}?{query}" if query else url


def build_root(node):
    """Return `node` with the JSON-LD ``@context`` prepended."""
    return {"@context": CONTEXT, **node}


class Bioschema:
    """
    Base class for a Bioschemas profile node built from a model instance.

    Subclasses set `profile` (a key into `PROFILES`) and override `fields()`
    for properties present in both the minimal and full node, plus
    `extra_fields()` for properties added only when `minimal` is False.
    """

    profile = None

    def __init__(self, obj, request=None, minimal=False):
        self.obj = obj
        self.request = request
        self.minimal = minimal

    @property
    def url(self):
        return _absolute_url(self.request, self.obj.get_absolute_url())

    @property
    def main_entity_of_page(self):
        """The rendered page's URL, when it differs from the node's own `url`."""
        page = _current_page_url(self.request)
        return page if page and page != self.url else None

    def fields(self):
        """Properties present in both the minimal and full node."""
        return {}

    def extra_fields(self):
        """Properties added only when `minimal` is False."""
        return {}

    def build(self):
        node = _build_node(self.profile)
        node.update(self.fields())
        if not self.minimal:
            node.update(self.extra_fields())
        return _drop_empty(node)


# --- shared nodes --------------------------------------------------------


def build_organization():
    """Return the BCA consortium as a schema.org Organization node."""
    website = _get_setting("BCA_WEBSITE", "https://biodiversitycellatlas.org")
    return _drop_empty(
        {
            "@type": "Organization",
            "@id": website,
            "name": "Biodiversity Cell Atlas",
            "url": website,
            "email": _get_setting("BCA_EMAIL"),
        }
    )


def get_data_license():
    """Return the portal-wide data license URL."""
    return _get_setting("BCA_DATA_LICENSE", "https://creativecommons.org/licenses/by/4.0/")


def build_data_download(request, url, name, fmt, description=None):
    """Return a DataDownload node for `url` in the given format."""
    return _drop_empty(
        {
            "@type": "DataDownload",
            "name": name,
            "description": description,
            "encodingFormat": FORMATS.get(fmt, fmt),
            "contentUrl": _absolute_url(request, url),
        }
    )


def build_api_distributions(request, view, label, query=None, formats=("json", "csv", "tsv")):
    """Return DataDownload nodes for a REST endpoint in each output format."""
    downloads = []
    for fmt in formats:
        params = "&".join(filter(None, [query, f"format={fmt}"]))
        url = _safe_reverse(view, params)
        if url:
            downloads.append(build_data_download(request, url, f"{label} ({fmt.upper()})", fmt))
    return downloads


def build_species_file_distributions(request, species_list):
    """Return DataDownload nodes for the downloadable files of each species."""
    downloads = []
    for species in species_list or []:
        for each in species.files.all():
            url = _safe_reverse("download_file", args=[each.slug])
            if not url:  # pragma: no cover - defensive, mirrors _safe_reverse's NoReverseMatch guard
                continue
            ext = (each.ext or "").lower()
            downloads.append(
                build_data_download(
                    request,
                    url,
                    name=each.label,
                    fmt=FILE_FORMATS.get(ext, DEFAULT_FILE_FORMAT),
                    description=each.get_type_display(),
                )
            )
    return downloads


def build_scholarly_article(publication):
    """
    Return a publication as a schema.org ScholarlyArticle node.

    No conformance is claimed: Bioschemas' only ScholarlyArticle profile is a
    draft, so this stays a plain schema.org node.
    """
    if publication is None:
        return None

    url = _safe_query_url(publication)
    identifiers = [
        {
            "@type": "PropertyValue",
            "name": name,
            "propertyID": property_id,
            "value": value,
        }
        for name, property_id, value in (
            ("DOI", "https://registry.identifiers.org/registry/doi", publication.doi),
            ("PubMed ID", "https://registry.identifiers.org/registry/pubmed", publication.pmid),
        )
        if value
    ]
    authors = [{"@type": "Person", "name": name.strip()} for name in publication.authors.split(",") if name.strip()]

    return _drop_empty(
        {
            "@type": "ScholarlyArticle",
            "@id": url,
            "name": publication.title,
            "url": url,
            "identifier": identifiers,
            "author": authors,
            "datePublished": str(publication.year) if publication.year else None,
            "isPartOf": {"@type": "Periodical", "name": publication.journal},
        }
    )


# --- Taxon / TaxonName -------------------------------------------------------


class TaxonName(Bioschema):
    """TaxonName node (Bioschemas TaxonName 1.0-RELEASE). Required: name."""

    profile = "TaxonName"

    def fields(self):
        return {"name": self.obj.scientific_name, "taxonRank": TAXON_RANK}


class Taxon(Bioschema):
    """
    Taxon node for a species (Bioschemas Taxon 1.0-RELEASE).

    Required: name, taxonRank -- both always present, so even the minimal
    form (used for nested references) is profile-conformant.
    """

    profile = "Taxon"

    def fields(self):
        url = self.url
        return {
            "@id": url,
            "additionalType": DWC_TAXON,
            "name": self.obj.scientific_name,
            "taxonRank": TAXON_RANK,
            "url": url,
        }

    def extra_fields(self):
        species = self.obj
        taxon_id = _species_meta(species, "taxon_id")
        identifier = same_as = None
        if taxon_id:
            identifier = {
                "@type": "PropertyValue",
                "name": "NCBI Taxonomy ID",
                "propertyID": "https://registry.identifiers.org/registry/taxonomy",
                "value": taxon_id.value,
                "url": taxon_id.query_url,
            }
            same_as = taxon_id.query_url

        return {
            "identifier": identifier,
            "sameAs": same_as,
            "scientificName": TaxonName(species).build(),
            "vernacularName": species.common_name,
            "description": species.description,
            "image": species.image_url,
            "parentTaxon": self.parent_taxon,
            "mainEntityOfPage": self.main_entity_of_page,
        }

    @property
    def parent_taxon(self):
        # `division` is the botanical/mycological name for the same rank as
        # `phylum`, so both outrank the broader `kingdom`.
        for key in ("phylum", "division", "kingdom"):
            parent = _species_meta(self.obj, key)
            if parent:
                return parent.value
        return None


# --- Gene --------------------------------------------------------------------


class Gene(Bioschema):
    """
    Gene node (Bioschemas Gene 1.0-RELEASE). Required: identifier, name.

    ``@id`` and ``url`` always point at the canonical ``entry/gene/...`` page
    so that the Cell Atlas gene view does not claim a second, competing
    entity; that view is recorded as ``mainEntityOfPage`` instead.
    """

    profile = "Gene"

    def fields(self):
        url = self.url
        return {
            "@id": url,
            "identifier": self.obj.slug,
            "name": self.obj.name,
            "url": url,
        }

    def extra_fields(self):
        obj = self.obj
        return {
            "description": obj.description,
            "taxonomicRange": Taxon(obj.species, self.request, minimal=True).build(),
            "hasBioChemEntityPart": [self._domain_node(domain) for domain in obj.domains.all()],
            "isPartOfBioChemEntity": [self._orthogroup_node(group) for group in obj.orthogroups.all()],
            "mainEntityOfPage": self.main_entity_of_page,
        }

    def _domain_node(self, domain):
        return _drop_empty(
            {
                "@type": "BioChemEntity",
                "name": domain.name,
                "identifier": domain.name,
                "sameAs": _safe_query_url(domain),
            }
        )

    def _orthogroup_node(self, group):
        return _drop_empty(
            {
                "@type": "BioChemEntity",
                "@id": _absolute_url(self.request, group.get_absolute_url()),
                "name": group.name,
                "description": "Orthogroup",
            }
        )


# --- Dataset -----------------------------------------------------------------


class Dataset(Bioschema):
    """
    Dataset node (Bioschemas Dataset 1.0-RELEASE).

    Required: description, identifier, keywords, license, name, url -- all
    six are emitted for both the full and the minimal form, so nested
    dataset nodes inside a DataCatalog stay profile-conformant.
    """

    profile = "Dataset"

    @property
    def description(self):
        obj = self.obj
        return (
            obj.description
            or obj.species.description
            or f"Single-cell transcriptomic dataset for {obj.species.scientific_name} in the Biodiversity Cell Atlas."
        )

    @property
    def keywords(self):
        obj = self.obj
        keywords = [*BASE_KEYWORDS, obj.species.scientific_name]
        if obj.species.common_name:
            keywords.append(obj.species.common_name)
        if obj.name:
            keywords.append(obj.name)
        return keywords

    def fields(self):
        url = self.url
        return {
            "@id": url,
            "identifier": url,
            "name": str(self.obj),
            "description": self.description,
            "url": url,
            "keywords": self.keywords,
            "license": get_data_license(),
        }

    def extra_fields(self):
        obj = self.obj
        return {
            "creator": build_organization(),
            "publisher": build_organization(),
            "isAccessibleForFree": True,
            "measurementTechnique": MEASUREMENT_TECHNIQUE,
            "variableMeasured": ["gene expression", "UMI counts", "cell counts"],
            "about": Taxon(obj.species, self.request, minimal=True).build(),
            "dateCreated": obj.date_created,
            "dateModified": obj.date_updated,
            "citation": build_scholarly_article(obj.publication),
            "distribution": self._distributions(),
            "includedInDataCatalog": build_catalog_reference(self.request),
            "image": obj.get_image_url(),
            "mainEntityOfPage": self.main_entity_of_page,
        }

    def _distributions(self):
        obj = self.obj
        query = f"dataset={obj.slug}"
        endpoints = [
            ("rest:dataset-list", "Dataset information"),
            ("rest:metacell-list", "Metacells"),
            ("rest:metacellcount-list", "Metacell counts"),
            ("rest:singlecell-list", "Single cells"),
        ]
        downloads = []
        for view, label in endpoints:
            downloads += build_api_distributions(self.request, view, f"{obj} - {label}", query=query)
        return downloads


# --- DataCatalog -------------------------------------------------------------


CATALOG_NAME = "Biodiversity Cell Atlas Data Portal"
CATALOG_DESCRIPTION = (
    "Single-cell transcriptomic atlases across the eukaryotic tree of life: "
    "browse, explore and download cell types, gene expression and gene modules "
    "for every species in the Biodiversity Cell Atlas."
)


def build_catalog_reference(request=None):
    """Return a minimal reference to the portal DataCatalog."""
    url = _absolute_url(request, _safe_reverse("index") or "/")
    return _drop_empty({"@type": "DataCatalog", "@id": url, "name": CATALOG_NAME, "url": url})


class DataCatalog(Bioschema):
    """
    DataCatalog node (Bioschemas DataCatalog 0.3-RELEASE-2019_07_01).

    Required: description, name, url, keywords, provider.

    Unlike the other profiles, a catalog isn't built from a single model
    instance, so its fields come from keyword arguments instead of `obj`.
    """

    profile = "DataCatalog"

    def __init__(self, request=None, name=None, description=None, datasets=None, distributions=None, keywords=None):
        super().__init__(obj=None, request=request)
        self.name = name or CATALOG_NAME
        self.description = description or CATALOG_DESCRIPTION
        self.datasets = datasets
        self.distributions = distributions
        self.keywords = keywords or BASE_KEYWORDS

    @property
    def index_url(self):
        return _absolute_url(self.request, _safe_reverse("index") or "/")

    @property
    def url(self):
        return _current_page_url(self.request) or self.index_url

    def fields(self):
        index_url = self.index_url
        node = {
            "@id": index_url,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "keywords": self.keywords,
            "provider": build_organization(),
            "license": get_data_license(),
            "identifier": index_url,
        }
        if self.datasets:
            # Minimal-but-conformant Dataset nodes; on paginated pages this
            # describes the datasets shown on that page.
            node["dataset"] = [Dataset(each, self.request, minimal=True).build() for each in self.datasets]
        if self.distributions:
            node["distribution"] = self.distributions
        return node


# --- list pages --------------------------------------------------------------


def build_item_list_page(objects, request=None, builder=None, name=None):
    """
    Build a CollectionPage wrapping an ItemList of entity stubs.

    List pages have no Bioschemas profile of their own, so no conformance is
    claimed; the items themselves are minimal profile-conformant nodes.
    """
    builder = builder or (lambda obj, req: {})
    items = [
        {"@type": "ListItem", "position": position, "item": builder(obj, request)}
        for position, obj in enumerate(objects, start=1)
    ]

    return _drop_empty(
        {
            "@type": "CollectionPage",
            "url": _current_page_url(request),
            "name": name,
            "mainEntity": {
                "@type": "ItemList",
                "numberOfItems": len(items),
                "itemListElement": items,
            },
        }
    )
