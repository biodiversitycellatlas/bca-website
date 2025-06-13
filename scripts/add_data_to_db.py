#!/usr/bin/env python3

from django.core.exceptions import ValidationError
from django.db.models import F, Count, Avg, Sum, OuterRef, Subquery

from collections import Counter
from rds2py import read_rds
import subprocess
import time

import csv
import json
import xml.etree.ElementTree as ET
import yaml

import numpy as np
import pandas as pd

import urllib.request
import urllib.parse
import warnings
import re

from app import models

import functools
import psycopg2
import psutil

# Auto-flush print statements
print = functools.partial(print, flush=True)

####### Utility functions

def print_progress(index, total):
    perc = int(index/total * 100)
    msg = f"{perc}% ({index} out of {total})"
    print(msg)
    return msg

def print_memory_usage(val=" "):
    mem = psutil.virtual_memory()
    mem_used = mem.used / 1024**2
    mem_total = mem.total / 1024**2
    mem_free = mem.available / 1024**2
    print(f"Memory {val} | Used {mem_used:.2f} MB out of {mem_total:.2f} MB (free: {mem_free:.2f} MB)")


def validate_and_bulk_create(obj, arr):
    #for data in arr:
    #    try:
    #        data.full_clean()
    #    except ValidationError:
    #        print(f"Validation error for {instance}: {e}")

    return obj.objects.bulk_create(arr, ignore_conflicts=True)


def batch_raw_insert(cursor, model, cols, batch):
    import io
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t')
    writer.writerows(batch)
    output.seek(0)

    table = model._meta.db_table
    columns = ', '.join(cols)
    sql = f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t')"
    cursor.copy_expert(sql, output)
    cursor.connection.commit()
#
#   # Add via raw SQL
#   placeholders = '(' + ','.join(['%s'] * len(cols)) + ')'
#
#   cols = ", ".join(cols)
#   cols = f"({cols})"
#
#   args = ','.join(cursor.mogrify(placeholders, row) for row in batch)
#   cursor.execute(f"INSERT INTO {table} {cols} VALUES {args} ON CONFLICT DO NOTHING")


def perform_subquery(obj, expr):
    """ Return subquery for aggregated statistics per object. """
    subquery = Subquery(obj.filter(id=OuterRef('id')).annotate(
        expr=expr
    ).values('expr')[:1])
    return subquery


####### Main functions

def add_taxonomy_metadata(species):
    (ncbi, _) = models.Source.objects.get_or_create(
        name='NCBI Taxonomy',
        description='NCBI Taxonomy Database',
        url='https://www.ncbi.nlm.nih.gov/',
        query_url='https://www.ncbi.nlm.nih.gov/datasets/taxonomy/{{id}}')

    scientific_name = species.scientific_name
    # Fetch taxonomy ID for this species
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    term = urllib.parse.quote(f"{scientific_name}")
    url = f"{base_url}esearch.fcgi?db=taxonomy&term={term}&retmode=json"
    with urllib.request.urlopen(url) as response:
        data = json.load(response)

    try:
        taxid = data['esearchresult']['idlist'][0]
    except:
        raise ValueError(f"Taxonomy ID for species '{scientific_name}' not found.")

    # Fetch taxonomy details in XML
    fetch_url = f"{base_url}efetch.fcgi?db=taxonomy&id={taxid}&retmode=xml"
    with urllib.request.urlopen(fetch_url) as response:
        xml_data = response.read()

    tree = ET.ElementTree(ET.fromstring(xml_data))
    root = tree.getroot()

    # Parse taxonomy details
    m_list = [ models.Meta(species=species, key="taxon_id", value=taxid,
                           source=ncbi, query_term=taxid) ]

    m = models.Meta(species=species, key="division",
                    value=root.find('.//Division').text,
                    source=ncbi)
    m_list.append(m)

    for taxon in root.findall(".//Taxon"):
        rank = taxon.find("Rank").text
        name = taxon.find("ScientificName").text
        term = taxon.find("TaxId").text
        if rank and name:
            m = models.Meta(species=species, key=rank, value=name,
                            source=ncbi, query_term=term)
            m_list.append(m)
    return validate_and_bulk_create(models.Meta, m_list)


def add_species(name, dataset_name):
    (species, exists) = models.Species.objects.get_or_create(scientific_name=name)
    (dataset, exists) = species.datasets.get_or_create(name=dataset_name)

    # add taxonomy and other metadata
    add_taxonomy_metadata(species)
    return species, dataset


def add_metacells(dataset, mc2d, mc_annot, r_colors):
    mc_x  = mc2d['attributes']['mc_x']['data'].tolist()
    mc_y  = mc2d['attributes']['mc_y']['data'].tolist()
    mc_id = mc2d['attributes']['mc_x']['attributes']['names']['data']
    mc_list = []
    for idx, val in enumerate(mc_x):
        this_id = mc_id[idx]
        this_annot = mc_annot.loc[mc_annot['metacell'] == int(this_id)]
        type       = this_annot['cell_type'].values[0]

        color_key = [key for key in this_annot if "color" in key][0]
        color     = this_annot[color_key].values[0]

        if not color.startswith('#'):
            color = r_colors[r_colors['name'] == color]['hex'].values[0]
        mct, created = models.MetacellType.objects.get_or_create(
            dataset=dataset, name=type.replace("_", " "), color=color)

        # Avoid adding nan
        x = None if pd.isna(mc_x[idx]) else mc_x[idx]
        y = None if pd.isna(mc_y[idx]) else mc_y[idx]

        mc = models.Metacell(dataset=dataset, name=this_id, x=x, y=y, type=mct)
        mc_list.append(mc)

    return validate_and_bulk_create(models.Metacell, mc_list)


def add_metacell_links(dataset, mc2d):
    links_fr = mc2d['attributes']['graph']['data'][0]['data'].astype(int).tolist()
    links_to = mc2d['attributes']['graph']['data'][1]['data'].astype(int).tolist()
    mc_links_list = []
    for idx, fr in enumerate(links_fr):
        to = links_to[idx]
        if fr != to:
            mc_link = models.MetacellLink(
                dataset=dataset,
                metacell =models.Metacell.objects.filter(dataset=dataset, name=fr)[0],
                metacell2=models.Metacell.objects.filter(dataset=dataset, name=to)[0])
            mc_links_list.append(mc_link)

    return validate_and_bulk_create(models.MetacellLink, mc_links_list)


def add_metacell_stats(dataset):
    mcs = dataset.metacells.all()

    cells = perform_subquery(mcs, Count('singlecell'))
    umis  = perform_subquery(mcs, Sum('mge__umi_raw'))

    qs = mcs.annotate(
        metacell_id=F('id'),
        cells=cells,
        umis=umis
    ).values('metacell_id', 'cells', 'umis', 'dataset_id')

    metacell_count_list = [
        models.MetacellCount(
            metacell_id=row['metacell_id'],
            dataset_id=row['dataset_id'],
            cells=row['cells'],
            umis=row['umis'],
        )
        for row in qs
    ]
    return validate_and_bulk_create(models.MetacellCount, metacell_count_list)


def add_single_cells(dataset, mc2d, cellmc):
    sc_x  = mc2d['attributes']['sc_x']['data'].tolist()
    sc_y  = mc2d['attributes']['sc_y']['data'].tolist()
    sc_id = mc2d['attributes']['sc_x']['attributes']['dimnames']['data'][0]['data']

    # Single cell: 2D projection
    sc_x_dict = dict(zip(sc_id, sc_x))
    sc_y_dict = dict(zip(sc_id, sc_y))

    # Cell to metacell assignment
    cell2mc_metacells = cellmc.as_list()
    cell2mc_cells     = cellmc.names.as_list()
    cell2mc_metacells = [str(int(num)) if num.is_integer() else str(num) for num in cell2mc_metacells]
    cell2mc_dict  = dict(zip(cell2mc_cells, cell2mc_metacells))

    # Get all metacells
    mc_dict = {str(obj): obj for obj in
        models.Metacell.objects.filter(dataset=dataset)}

    sc_list = []
    for name in cell2mc_cells:
        metacell_name = str(int(cell2mc_dict[name]))
        m = mc_dict[metacell_name] if metacell_name in mc_dict else None
        x = sc_x_dict[name] if name in sc_x_dict else None
        y = sc_y_dict[name] if name in sc_y_dict else None

        # Avoid adding nan
        x = None if pd.isna(x) else x
        y = None if pd.isna(y) else y

        sc = models.SingleCell(dataset=dataset, name=name, x=x, y=y, metacell=m)
        sc_list.append(sc)

    return validate_and_bulk_create(models.SingleCell, sc_list)


def add_genes(species, gene_annot):
    if gene_annot.iloc[0, 0].lower().startswith(('gene', 'v1')):
        gene_annot = gene_annot.iloc[1:].reset_index(drop=True)

    # Assume the column with more / contains the domains
    n_slash_col1 = sum(x.count('/') for x in list(gene_annot[1]) if isinstance(x, str))
    n_slash_col2 = sum(x.count('/') for x in list(gene_annot[2]) if isinstance(x, str))

    if n_slash_col1 > n_slash_col2 and str(species) not in ["Spongilla lacustris"]:
        col_names = ["gene", "domains", "description"]
    else:
        col_names = ["gene", "description", "domains"]
    gene_annot.columns = col_names + list(gene_annot.columns[3:])

    # Split domains by / and ignore certain characters
    gene_annot['domains'] = gene_annot['domains'].apply(
        lambda e: list(set(
            [d for d in str(e).split('/')
                if pd.notna(e) and d and d not in ['nan', '-', '""'] ])))

    # Add domains to database
    domain_list = []
    domains = set(d for sublist in gene_annot['domains'] for d in sublist)
    for domain in domains:
        domain_list.append(models.Domain(name=domain))
    validate_and_bulk_create(models.Domain, domain_list)

    # Get dict with all domains
    all_domains = models.Domain.objects.filter(name__in=domains)
    domain_map = {d.name: d for d in all_domains}

    # Parse gene description (up to 400 characters)
    gene_annot['description'] = gene_annot['description'].apply(
        lambda x: None
            if pd.isna(x) or x in ['nan', '-']
            else x.replace('_', ' ')[:400]
    )

    # Add genes to database
    gene_list = []
    for index, row in gene_annot.iterrows():
        g = models.Gene(
            species=species, name=row['gene'], description=row['description'])
        gene_list.append(g)
    genes = validate_and_bulk_create(models.Gene, gene_list)

    all_genes = models.Gene.objects.filter(name__in=genes)
    gene_map = {g.name: g for g in all_genes}

    # Assign domains to genes
    through_model = models.Gene.domains.through
    relations = []
    for g, (_, row) in zip(genes, gene_annot.iterrows()):
        for domain_name in row['domains']:
            relations.append(through_model(
                gene=gene_map[g.name], domain=domain_map[domain_name]))
    validate_and_bulk_create(through_model, relations)
    return True


def add_metacell_gene_expression(species, dataset, expr, umi, umifrac):
    expr_df = pd.DataFrame(expr.matrix, expr.dimnames[0], expr.dimnames[1])
    umi_df = pd.DataFrame(umi.matrix, umi.dimnames[0], umi.dimnames[1])
    umifrac_df = pd.DataFrame(umifrac.matrix, umifrac.dimnames[0], umifrac.dimnames[1])

    # Prefetch all metacells and genes into dicts
    mc_dict = {str(obj): obj for obj in models.Metacell.objects.filter(dataset=dataset)}
    gene_dict = {str(obj): obj for obj in models.Gene.objects.filter(species=species)}

    index = 0
    mge_list = []
    total = umi_df.shape[0] * umi_df.shape[1]
    for gene, row in umi_df.iterrows():
        # Skip genes not in database (such as orphan peaks)
        if gene not in gene_dict.keys():
            continue

        for metacell in umi_df.columns:
            umi_value = row[metacell]

            try:
                umifrac_value = umifrac_df.loc[gene, metacell]
            except:
                umifrac_value = None

            try:
                fold_change_value = expr_df.loc[gene, metacell]
            except:
                fold_change_value = None

            mge = models.MetacellGeneExpression(
                dataset=dataset, gene=gene_dict[gene], metacell=mc_dict[metacell],
                fold_change=fold_change_value,
                umi_raw=umi_value, umifrac=umifrac_value)
            mge_list.append(mge)

            # Save to database every 100k iterations (less memory pressure)
            if index % 100000 == 0 and index != 0:
                validate_and_bulk_create(models.MetacellGeneExpression, mge_list)
                mge_list = []
                print_progress(index, total)
            index = index + 1
    return validate_and_bulk_create(models.MetacellGeneExpression, mge_list)


def add_sc_gene_expression(species, dataset, counts):
    start_time = time.time()

    dataset_id = dataset.id
    genes, scs = counts.dimnames
    counts_csc = counts.matrix.tocsc()

    print_memory_usage()
    # Check genes that appear more than once to ignore them later
    genes_dup = [g for g in genes if Counter(genes)[g] > 1]

    # Prefetch all metacells and genes into dicts
    sc_dict = {str(obj): obj.id for obj in models.SingleCell.objects.filter(dataset=dataset)}
    gene_dict = {str(obj): obj.id for obj in models.Gene.objects.filter(species=species)}
    all_genes = gene_dict.keys()

    scge_list = []
    n_cols = counts_csc.shape[1]
    cols = ['umi_raw', 'umifrac', 'dataset_id', 'gene_id', 'single_cell_id']

    connection = psycopg2.connect(host=os.environ.get("POSTGRES_HOST"))

    with connection.cursor() as cursor:
        for j in range(n_cols):
            col = counts_csc.getcol(j)
            col_sum = col.sum()
            if col_sum == 0:
                continue

            col = col.tocoo()
            for i, umi_raw in zip(col.row, col.data):
                # Skip genes not found (e.g., orphan peaks) or if umi_raw is 0
                if genes[i] not in all_genes or umi_raw == 0:
                    continue

                # Skip if gene is duplicate
                if genes[i] in genes_dup:
                    continue


                # Calculate umifrac from umi_raw's total count per single cell
                umifrac = (umi_raw * 10000) / col_sum

                scge = (umi_raw, umifrac, dataset_id,
                    gene_dict[genes[i]], sc_dict[scs[j]])
                scge_list.append(scge)

                # Save to database every 100k iterations (less memory pressure)
                if len(scge_list) >= 100000:
                    batch_raw_insert(cursor, models.SingleCellGeneExpression, cols, scge_list)
                    scge_list = []
                    print_progress(j, n_cols)

        if scge_list:
            batch_raw_insert(cursor, models.SingleCellGeneExpression, cols, scge_list)
    connection.close()

    # Print elapsed time
    elapsed = time.time() - start_time
    print("Wall time:", time.strftime('%Mm:%Ss', time.gmtime(elapsed)))
    return True


def add_species_data(species_config, dir, r_colors, load, force=False):
    name = species_config['species']
    match = re.match(r"^(.*?)\s*\((.*?)\)$", name)

    if match:
        species_name = match.group(1)
        dataset_name = match.group(2)
    else:
        species_name = name
        dataset_name = None

    # Remove last character in sp. (for safety)
    if species_name.endswith("sp."):
        species_name = species_name[:-1]

    (species, dataset) = add_species(species_name, dataset_name)

    # check loading conditions for different components
    load_metacells = load['metacells'] and (force or not dataset.metacells.exists())
    load_sc        = load['sc']        and (force or not dataset.sc.exists())
    load_genes     = load['genes']     and (force or not species.genes.exists())
    load_mge       = load['mge']       and (force or not dataset.mge.exists())
    load_scge      = load['scge']      and (force or not dataset.scge.exists())
    load_mc_stats  = load['mc_stats']  and (force or not dataset.metacell_stats.exists())

    # avoid common warning of no relevance
    if load_metacells or load_sc:
        f_mc2d = dir + species_config['mc2d_file']
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore', message=".*RDS file contains an unknown class: 'tgMC2D'.*")
            mc2d = read_rds(f_mc2d)

    if load_metacells:
        f_annot = dir + species_config['ann_file']
        print(f"Adding metacells from {f_mc2d} and {f_annot}...")
        mc_annot = pd.read_csv(f_annot, sep="\t")
        add_metacells(dataset, mc2d, mc_annot, r_colors)

        print(f"Adding metacell links from {f_mc2d}...")
        add_metacell_links(dataset, mc2d)

    if load_sc:
        f_cellmc = dir + species_config['cellmc_file']
        print(f"Adding single cells from {f_mc2d} and {f_cellmc}...")
        cellmc = read_rds(f_cellmc)
        add_single_cells(dataset, mc2d, cellmc)

    if load_genes:
        f = dir + species_config['gene_annot_file']
        print(f"Adding genes from {f}...")
        gene_annot = pd.read_csv(f, sep="\t", header=None)
        add_genes(species, gene_annot)

    if load_mge:
        f_fc = dir + species_config['mcfp_file']
        f_umi = dir + species_config['umicount_file']
        f_umifrac = dir + species_config['umifrac_file']

        print(f"Adding gene expression per metacell from {f_fc}, {f_umi} and {f_umifrac}...")
        fc = read_rds(f_fc)
        umi = read_rds(f_umi)
        umifrac = read_rds(f_umifrac)
        add_metacell_gene_expression(species, dataset, fc, umi, umifrac)

    if load_mc_stats:
        # Requires metacell gene expression data
        print(f"Adding metacell stats...")
        add_metacell_stats(dataset)

    if load_scge:
        f = dir + species_config['umicountsc_file']
        print(f"Adding gene expression per single cell from {f}...")
        counts = read_rds(f)
        add_sc_gene_expression(species, dataset, counts)

def addOrthologGroups(data_dir):
    print("Loading orthologous groups...")
    ortholog_groups = pd.read_csv(f"{data_dir}/orthologous_groups.txt", sep="\t")

    gene_dict = {}
    for obj in models.Gene.objects.all():
        gene_dict[str(obj)] = obj

    og_list = []
    for index, row in ortholog_groups.iterrows():
        (group, genes) = row
        for gene in genes.split(" "):
            if gene in gene_dict:
                og = models.Ortholog(orthogroup=group, gene=gene_dict[gene], species_id=gene_dict[gene].species_id)
                og_list.append(og)
    return validate_and_bulk_create(models.Ortholog, og_list)


def main(data_dir, load, filter=[], exclude=['nvec_old'], force=False):
    r_colors_file = f"{data_dir}/R_colors.tsv"
    r_colors = pd.read_csv(r_colors_file, sep="\t")

    config = f"{data_dir}/config.yaml"
    with open(config) as file:
        data = yaml.safe_load(file)

    for key, species_config in data.items():
        if key in exclude or key == 'default':
            continue

        if filter != [] and key not in filter:
            continue
        species_dir = f"{data_dir}/{species_config['data_subdir']}/"

        print("\n================================================================")
        print(f"Processing species {species_config['species']} [{key}]...")
        add_species_data(species_config, species_dir, r_colors, load, force)

    if load['orthologs']:
        addOrthologGroups(data_dir)

    print('All done!')

load = {
    'metacells': True,
    'sc': True,
    'genes': True,
    'mge': True,
    'mc_stats': True,
    'scge': True,
    'orthologs': True
}

data_dir = "data/raw"
#data_dir = "app/static/app/data"

#main(data_dir, load)
print_memory_usage()
main(data_dir, load, exclude=['nvec_old', 'dmel'])
print_memory_usage()
