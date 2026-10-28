import pickle

from app.models import Dataset, MetacellType, MetacellTypeSimilarity

d1 = Dataset.objects.get(species__scientific_name="Nematostella vectensis")
d2 = Dataset.objects.get(species__scientific_name="Stylophora pistillata", name="coral")

d1_genes = dict(d1.species.genes.values_list("name", "id"))
d2_genes = dict(d2.species.genes.values_list("name", "id"))

with open("data/raw/nvec-spis_coral.gene_pairs.pkl", "rb") as f:
    df = pickle.load(f)

pair_columns = [c for c in df.columns if not c.endswith("_pval1") and not c.endswith("_pval2")]

for column in pair_columns:
    source_type, target_type = column.split(";")

    source_type = source_type.split("_", 1)[1].replace("_", " ")
    target_type = target_type.split("_", 1)[1].replace("_", " ")

    try:
        source = d1.metacell_types.get(name=source_type)
        target = d2.metacell_types.get(name=target_type)
    except MetacellType.DoesNotExist:
        print(f"Metacell type pair not found: {source_type}, {target_type}")
        continue

    gene_pairs = []

    for value in df[column].dropna():
        source_gene, target_gene = value.split(";")
        source_prefix, source_gene = source_gene.split("_", 1)
        target_prefix, target_gene = target_gene.split("_", 1)

        try:
            gene_pairs.append([d1_genes[source_gene], d2_genes[target_gene]])
        except KeyError:
            print(f"Gene(s) not found: {source_gene}, {target_gene}")

    try:
        similarity = MetacellTypeSimilarity.objects.get(
            metacelltype=source,
            metacelltype2=target,
        )
        reverse = False
    except MetacellTypeSimilarity.DoesNotExist:
        similarity = MetacellTypeSimilarity.objects.get(
            metacelltype=target,
            metacelltype2=source,
        )
        reverse = True

    if reverse:
        gene_pairs = [[b, a] for a, b in gene_pairs]

    similarity.samap_gene_pairs = gene_pairs or None
    similarity.save(update_fields=["samap_gene_pairs"])
    print(f"Updated {source.name} -> {target.name}: {len(gene_pairs)} gene pairs")
