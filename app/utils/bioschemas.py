"""
Bioschemas JSON-LD payload builders.

Each public function returns a plain ``dict`` describing one entity according to
a `Bioschemas profile <https://bioschemas.org/profiles/>`_. The dicts are
serialised into ``<script type="application/ld+json">`` blocks by the
``bioschemas`` template tags; keeping the payloads here makes them unit-testable
and keeps the profile versions in one place.

Only *released* profiles are targeted, since those are what the Bioschemas
validator and the ELIXIR harvesters expect. Draft profiles were prototyped for
the protein-domain pages and the nested citation node and then withdrawn -- see
section 10 of `report-bioschemas.md` for what was removed and why. Nested nodes
never carry their own ``@context``: :func:`as_root` adds it to the top-level
node only.
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


def _setting(key, default=None):
    """Return a setting, falling back to `default` when unset."""
    return getattr(settings, key, default)


def _absolute(request, url):
    """Return `url` as an absolute URI, when a request is available."""
    if not url:
        return None
    if request is None:
        return url
    return request.build_absolute_uri(url)


def _page_url(request):
    """Return the absolute URI of the page currently being rendered."""
    return request.build_absolute_uri() if request is not None else None


def _compact(value):
    """
    Recursively drop keys and items with no value.

    Bioschemas consumers treat an absent property and an empty one differently,
    so empty strings, lists and dicts are removed rather than emitted. Booleans
    and zeroes are kept.
    """
    if isinstance(value, dict):
        items = ((key, _compact(val)) for key, val in value.items())
        return {key: val for key, val in items if not _is_empty(val)}
    if isinstance(value, (list, tuple)):
        items = (_compact(val) for val in value)
        return [val for val in items if not _is_empty(val)]
    return value


def _is_empty(value):
    """Return True for values that should be omitted from the payload."""
    if isinstance(value, (bool, int, float)):
        return False
    return value is None or value in ("", [], {})


def _node(type_, profile=None):
    """Start a JSON-LD node, optionally claiming conformance to a profile."""
    node = {"@type": type_}
    if profile:
        node["dct:conformsTo"] = {"@type": "CreativeWork", "@id": PROFILES[profile]}
    return node


def _meta(species, key):
    """Return a species `Meta` row by key, or None when absent."""
    return species.meta_set.filter(key=key).first()


def _query_url(obj):
    """
    Return an object's external query URL, tolerating a missing Source.

    `ExternalQueryMixin.source` does a `Source.objects.get()`, which raises when
    the source has not been loaded into the database.
    """
    try:
        return obj.query_url
    except ObjectDoesNotExist:
        return None


def _reverse(view, query=None, args=None):
    """Reverse a view name, returning None when the route does not exist."""
    try:
        url = reverse(view, args=args)
    except NoReverseMatch:  # pragma: no cover - defensive
        return None
    return f"{url}?{query}" if query else url


def as_root(node):
    """Return `node` with the JSON-LD ``@context`` prepended."""
    return {"@context": CONTEXT, **node}


# --- shared nodes ------------------------------------------------------------


def organization():
    """Return the BCA consortium as a schema.org Organization node."""
    website = _setting("BCA_WEBSITE", "https://biodiversitycellatlas.org")
    return _compact(
        {
            "@type": "Organization",
            "@id": website,
            "name": "Biodiversity Cell Atlas",
            "url": website,
            "email": _setting("BCA_EMAIL"),
        }
    )


def data_license():
    """Return the portal-wide data license URL."""
    return _setting("BCA_DATA_LICENSE", "https://creativecommons.org/licenses/by/4.0/")


def data_download(request, url, name, fmt, description=None):
    """Return a DataDownload node for `url` in the given format."""
    return _compact(
        {
            "@type": "DataDownload",
            "name": name,
            "description": description,
            "encodingFormat": FORMATS.get(fmt, fmt),
            "contentUrl": _absolute(request, url),
        }
    )


def api_distributions(request, view, label, query=None, formats=("json", "csv", "tsv")):
    """Return DataDownload nodes for a REST endpoint in each output format."""
    downloads = []
    for fmt in formats:
        params = "&".join(filter(None, [query, f"format={fmt}"]))
        url = _reverse(view, params)
        if url:
            downloads.append(data_download(request, url, f"{label} ({fmt.upper()})", fmt))
    return downloads


def species_file_distributions(request, species_list):
    """Return DataDownload nodes for the downloadable files of each species."""
    downloads = []
    for species in species_list or []:
        for each in species.files.all():
            url = _reverse("download_file", args=[each.slug])
            if not url:  # pragma: no cover - defensive, mirrors _reverse's NoReverseMatch guard
                continue
            ext = (each.ext or "").lower()
            downloads.append(
                data_download(
                    request,
                    url,
                    name=each.label,
                    fmt=FILE_FORMATS.get(ext, DEFAULT_FILE_FORMAT),
                    description=each.get_type_display(),
                )
            )
    return downloads


def scholarly_article(publication):
    """
    Return a publication as a schema.org ScholarlyArticle node.

    No conformance is claimed: Bioschemas' only ScholarlyArticle profile is a
    draft, so this stays a plain schema.org node.
    """
    if publication is None:
        return None

    url = _query_url(publication)
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

    return _compact(
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


def taxon_name(species):
    """
    Build a TaxonName node (Bioschemas TaxonName 1.0-RELEASE).

    Required: name.
    """
    node = _node("TaxonName", "TaxonName")
    node["name"] = species.scientific_name
    node["taxonRank"] = TAXON_RANK
    return _compact(node)


def taxon(species, request=None, minimal=False):
    """
    Build a Taxon node for a species (Bioschemas Taxon 1.0-RELEASE).

    Required: name, taxonRank -- both always present, so even the `minimal`
    form (used for nested references) is profile-conformant.
    """
    url = _absolute(request, species.get_absolute_url())

    node = _node("Taxon", "Taxon")
    node["@id"] = url
    node["additionalType"] = DWC_TAXON
    node["name"] = species.scientific_name
    node["taxonRank"] = TAXON_RANK
    node["url"] = url

    if minimal:
        return _compact(node)

    taxon_id = _meta(species, "taxon_id")
    if taxon_id:
        node["identifier"] = {
            "@type": "PropertyValue",
            "name": "NCBI Taxonomy ID",
            "propertyID": "https://registry.identifiers.org/registry/taxonomy",
            "value": taxon_id.value,
            "url": taxon_id.query_url,
        }
        node["sameAs"] = taxon_id.query_url

    node["scientificName"] = taxon_name(species)
    node["vernacularName"] = species.common_name
    node["description"] = species.description
    node["image"] = species.image_url

    # Use the most specific enclosing rank recorded for this species
    for key in ("phylum", "kingdom", "division"):
        parent = _meta(species, key)
        if parent:
            node["parentTaxon"] = parent.value
            break

    page = _page_url(request)
    if page and page != url:
        node["mainEntityOfPage"] = page

    return _compact(node)


# --- Gene --------------------------------------------------------------------


def gene(obj, request=None, minimal=False):
    """
    Build a Gene node (Bioschemas Gene 1.0-RELEASE).

    Required: identifier, name.

    ``@id`` and ``url`` always point at the canonical ``entry/gene/...`` page so
    that the Cell Atlas gene view does not claim a second, competing entity;
    that view is recorded as ``mainEntityOfPage`` instead.
    """
    url = _absolute(request, obj.get_absolute_url())

    node = _node("Gene", "Gene")
    node["@id"] = url
    node["identifier"] = obj.slug
    node["name"] = obj.name
    node["url"] = url

    if minimal:
        return _compact(node)

    node["description"] = obj.description
    node["taxonomicRange"] = taxon(obj.species, request, minimal=True)
    node["hasBioChemEntityPart"] = [
        _compact(
            {
                "@type": "BioChemEntity",
                "name": domain.name,
                "identifier": domain.name,
                "sameAs": _query_url(domain),
            }
        )
        for domain in obj.domains.all()
    ]
    node["isPartOfBioChemEntity"] = [
        _compact(
            {
                "@type": "BioChemEntity",
                "@id": _absolute(request, group.get_absolute_url()),
                "name": group.name,
                "description": "Orthogroup",
            }
        )
        for group in obj.orthogroups.all()
    ]

    page = _page_url(request)
    if page and page != url:
        node["mainEntityOfPage"] = page

    return _compact(node)


# --- Dataset -----------------------------------------------------------------


def dataset_description(obj):
    """
    Return a non-empty description for a dataset.

    ``description`` is required by the Dataset profile but nullable on both
    `Dataset` and `Species`, so fall back to a generated sentence.
    """
    if obj.description:
        return obj.description
    if obj.species.description:
        return obj.species.description
    return f"Single-cell transcriptomic dataset for {obj.species.scientific_name} in the Biodiversity Cell Atlas."


def dataset_keywords(obj):
    """Return the keyword list for a dataset."""
    keywords = list(BASE_KEYWORDS)
    keywords.append(obj.species.scientific_name)
    if obj.species.common_name:
        keywords.append(obj.species.common_name)
    if obj.name:
        keywords.append(obj.name)
    return keywords


def dataset_distributions(request, obj):
    """Return DataDownload nodes for the REST endpoints serving a dataset."""
    query = f"dataset={obj.slug}"
    endpoints = [
        ("rest:dataset-list", "Dataset information"),
        ("rest:metacell-list", "Metacells"),
        ("rest:metacellcount-list", "Metacell counts"),
        ("rest:singlecell-list", "Single cells"),
    ]
    downloads = []
    for view, label in endpoints:
        downloads += api_distributions(request, view, f"{obj} - {label}", query=query)
    return downloads


def dataset(obj, request=None, minimal=False):
    """
    Build a Dataset node (Bioschemas Dataset 1.0-RELEASE).

    Required: description, identifier, keywords, license, name, url -- all six
    are emitted for both the full and the `minimal` form, so nested dataset
    nodes inside a DataCatalog stay profile-conformant.
    """
    url = _absolute(request, obj.get_absolute_url())

    node = _node("Dataset", "Dataset")
    node["@id"] = url
    node["identifier"] = url
    node["name"] = str(obj)
    node["description"] = dataset_description(obj)
    node["url"] = url
    node["keywords"] = dataset_keywords(obj)
    node["license"] = data_license()

    if minimal:
        return _compact(node)

    node["creator"] = organization()
    node["publisher"] = organization()
    node["isAccessibleForFree"] = True
    node["measurementTechnique"] = MEASUREMENT_TECHNIQUE
    node["variableMeasured"] = ["gene expression", "UMI counts", "cell counts"]
    node["about"] = taxon(obj.species, request, minimal=True)
    node["dateCreated"] = obj.date_created
    node["dateModified"] = obj.date_updated
    node["citation"] = scholarly_article(obj.publication)
    node["distribution"] = dataset_distributions(request, obj)
    node["includedInDataCatalog"] = catalog_reference(request)
    node["image"] = obj.get_image_url()

    page = _page_url(request)
    if page and page != url:
        node["mainEntityOfPage"] = page

    return _compact(node)


# --- DataCatalog -------------------------------------------------------------


CATALOG_NAME = "Biodiversity Cell Atlas Data Portal"
CATALOG_DESCRIPTION = (
    "Single-cell transcriptomic atlases across the eukaryotic tree of life: "
    "browse, explore and download cell types, gene expression and gene modules "
    "for every species in the Biodiversity Cell Atlas."
)


def catalog_reference(request=None):
    """Return a minimal reference to the portal DataCatalog."""
    url = _absolute(request, _reverse("index") or "/")
    return _compact(
        {
            "@type": "DataCatalog",
            "@id": url,
            "name": CATALOG_NAME,
            "url": url,
        }
    )


def data_catalog(request=None, name=None, description=None, datasets=None, distributions=None, keywords=None):
    """
    Build a DataCatalog node (Bioschemas DataCatalog 0.3-RELEASE-2019_07_01).

    Required: description, name, url, keywords, provider.

    `datasets` are emitted as minimal-but-conformant Dataset nodes; on paginated
    pages this describes the datasets shown on that page.
    """
    index_url = _absolute(request, _reverse("index") or "/")
    page = _page_url(request) or index_url

    node = _node("DataCatalog", "DataCatalog")
    node["@id"] = index_url
    node["name"] = name or CATALOG_NAME
    node["description"] = description or CATALOG_DESCRIPTION
    node["url"] = page
    node["keywords"] = keywords or BASE_KEYWORDS
    node["provider"] = organization()
    node["license"] = data_license()
    node["identifier"] = index_url

    if datasets:
        node["dataset"] = [dataset(each, request, minimal=True) for each in datasets]
    if distributions:
        node["distribution"] = distributions

    return _compact(node)


# --- list pages --------------------------------------------------------------


def item_list(objects, request=None, builder=None, name=None):
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

    return _compact(
        {
            "@type": "CollectionPage",
            "url": _page_url(request),
            "name": name,
            "mainEntity": {
                "@type": "ItemList",
                "numberOfItems": len(items),
                "itemListElement": items,
            },
        }
    )
