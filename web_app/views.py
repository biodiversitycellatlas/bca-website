from django.shortcuts import render
import json
from rds2py import read_rds
from scipy.cluster.hierarchy import ward, leaves_list
import numpy as np
import pandas as pd

def index(request):
    return render(request, "web_app/index.html")


def atlas(request):
    mc2d = read_rds('web_app/static/web_app/data/tadh/tadh_reord_2dproj.RDS')
    r_colors = pd.read_csv('web_app/static/web_app/data/R_colors.tsv', sep="\t")

    # Prepare metacell data
    mc_annot = pd.read_csv('web_app/static/web_app/data/tadh/tadh_reord_metacell_annotation.tsv', sep="\t")

    mc_x  = mc2d['attributes']['mc_x']['data'].tolist()
    mc_y  = mc2d['attributes']['mc_y']['data'].tolist()
    mc_id = mc2d['attributes']['mc_x']['attributes']['names']['data']
    mc_array = []
    for idx, val in enumerate(mc_x):
        this_id = mc_id[idx]
        this_annot = mc_annot.loc[mc_annot['metacell'] == int(this_id)]
        type       = this_annot['cell_type'].values[0]
        color      = this_annot['cell_type_color'].values[0]
        color      = r_colors[r_colors['name'] == color]['hex'].values[0]
        mc_array.append({ "id": this_id, "x": mc_x[idx], "y": mc_y[idx], "cell_type": type, "color": color })

    # Prepare metacell links
    links_fr = mc2d['attributes']['graph']['data'][0]['data'].astype(int).tolist()
    links_to = mc2d['attributes']['graph']['data'][1]['data'].astype(int).tolist()
    links_array = []
    for idx, val in enumerate(links_fr):
        fr = mc_id.index(str( val ))
        to = mc_id.index(str( links_to[idx] ))
        if (mc_x[fr] != mc_x[to] and mc_y[fr] != mc_y[to]):
            links_array.append({"x": mc_x[fr], "y": mc_y[fr], "x2": mc_x[to], "y2": mc_y[to]})

    # Prepare single cell data
    sc_x  = mc2d['attributes']['sc_x']['data'].tolist()
    sc_y  = mc2d['attributes']['sc_y']['data'].tolist()
    sc_id = mc2d['attributes']['sc_x']['attributes']['dimnames']['data'][0]['data']
    
    cellmc       = read_rds('web_app/static/web_app/data/tadh/tadh_reord_metacell_assignments.RDS')
    cellmc_mcs   = cellmc.as_list()
    cellmc_names = cellmc.names.as_list()
    
    sc_array = []
    for idx, val in enumerate(sc_x):
        this_id  = sc_id[idx]
        metacell_id = cellmc_mcs[cellmc_names.index(this_id)]
        this_annot  = mc_annot[mc_annot['metacell'] == metacell_id]
        type       = this_annot['cell_type'].values[0]
        color      = this_annot['cell_type_color'].values[0]
        color      = r_colors[r_colors['name'] == color]['hex'].values[0]
        sc_array.append({"id": this_id, "x": sc_x[idx], "y": sc_y[idx], "metacell_type": type, "color": color})

    # Prepare heatmap with gene expression per metacell
    expr = read_rds('web_app/static/web_app/data/tadh/tadh_reord_metacell_gene_FC.RDS')
    gene_annot = pd.read_csv('web_app/static/web_app/data/tadh/Tadh_GENE_ANNOTATION.tsv', sep="\t", header=None)
    gene_annot.columns = ["gene", "domain", "domains"]

    minFC = 2
    scale_expression_fc = max(minFC, 6)
    gene_name, mc_name = expr.dimnames
    genes_per_cluster = 5

    # Convert to data frame
    m  = np.asmatrix(expr.matrix)
    df = pd.DataFrame(m, gene_name, mc_name)

    # Ignore genes starting with orphan
    filter_row = [row for row in df.index.tolist() if not row.startswith('orphan')]
    df = df.loc[filter_row]

    # Get genes with largest values (excluding those with fold-change < minFC)
    genes = [df[c].nlargest(genes_per_cluster) for c in df] # largest values
    genes = [i[i > minFC].index.tolist() for i in genes] # check fold-change
    genes = [i for x in genes for i in x] # flatten
    genes = list(set(genes)) # unique values
    df = df.loc[genes]

    # Exclude genes/metacells containing only missing values
    df = df.dropna(how='all').dropna(axis=1, how='all')

    # TODO: exclude genes based on transversality

    # Order metacells based on hierarchical clustering
    # mc_order = leaves_list(ward(df.corr())).tolist()
    # df = df.iloc[:, mc_order]

    # Order genes
    cols = df.columns.tolist()
    gene_ord = df.idxmax(axis=1)
    gene_ord = gene_ord.sort_values(key=lambda x: gene_ord.map(lambda v: -cols.index(v)))
    gene_ord = gene_ord.index.tolist()
    df = df.loc[gene_ord]

    # Transform min and max values
    df = df.clip(0, scale_expression_fc)

    gene_count, mc_count = df.shape
    df = df.stack()

    expr_array = []
    index = 1
    for (g, mc), val in df.items():
        if val >= minFC:
            index = index + 1
            this_mc_annot = mc_annot[mc_annot['metacell'] == int(mc)]
            mc_type       = this_mc_annot['cell_type'].values[0]
            mc_color      = this_mc_annot['cell_type_color'].values[0]

            this_gene_annot = gene_annot[gene_annot['gene'] == g]
            gene_domain     = this_gene_annot['domain'].values[0]
            if (pd.isnull(gene_domain)):
                gene_domain = "NA"

            gene_domains    = this_gene_annot['domains'].values[0]
            if (pd.isnull(gene_domains)):
                gene_domains = "NA"

            expr_array.append({"index": index, "value": val, "gene": g, "metacell": mc, "metacell_type": mc_type, "metacell_color": mc_color, "gene_domain": gene_domain, "gene_domains": gene_domains})

    context = {"sc_data": sc_array, "mc_data": mc_array, "mc_links": links_array, "expr": expr_array, "expr_genes": gene_count, "expr_mcs": mc_count}
    return render(request, "web_app/atlas.html", context)


def markers(request):
    return render(request, "web_app/markers.html")


def comparison(request):
    return render(request, "web_app/comparison.html")


def downloads(request):
    return render(request, "web_app/downloads.html")


def blog(request):
    return render(request, "web_app/blog.html")


def about(request):
    return render(request, "web_app/about.html")
