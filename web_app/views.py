from django.shortcuts import render
import json
import pandas
from rds2py import read_rds


def index(request):
    return render(request, "web_app/index.html")


def atlas(request):
    mc2d = read_rds('web_app/static/web_app/data/tadh/tadh_reord_2dproj.RDS')
    r_colors = pandas.read_csv('web_app/static/web_app/data/R_colors.tsv', sep="\t")

    # Prepare metacell data
    annot = pandas.read_csv('web_app/static/web_app/data/tadh/tadh_reord_metacell_annotation.tsv', sep="\t")

    mc_x  = mc2d['attributes']['mc_x']['data'].tolist()
    mc_y  = mc2d['attributes']['mc_y']['data'].tolist()
    mc_id = mc2d['attributes']['mc_x']['attributes']['names']['data']
    mc_array = []
    for idx, val in enumerate(mc_x):
        this_id = mc_id[idx]
        this_annot = annot.loc[annot['metacell'] == int(this_id)]
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
        this_annot  = annot[annot['metacell'] == metacell_id]
        type       = this_annot['cell_type'].values[0]
        color      = this_annot['cell_type_color'].values[0]
        color      = r_colors[r_colors['name'] == color]['hex'].values[0]
        sc_array.append({"id": this_id, "x": sc_x[idx], "y": sc_y[idx], "metacell_type": type, "color": color})

    expr = read_rds('web_app/static/web_app/data/tadh/tadh_reord_metacell_gene_FC.RDS')
    gene_annot = pandas.read_csv('web_app/static/web_app/data/tadh/Tadh_GENE_ANNOTATION.tsv', sep="\t", header=None)

    minFC = 2
    expr_array = []
    gene_name, mc_name = expr.dimnames
    for id_row, val_row in enumerate(expr.matrix):
        g = gene_name[id_row]
        val_row = val_row.tolist()
        for id_col, val_cell in enumerate(val_row):
            m = mc_name[id_col]
            if val_cell >= minFC:
                expr_array.append({"value": val_cell, "gene": g, "metacell": m})

    context = {"sc_data": sc_array, "mc_data": mc_array, "mc_links": links_array, "expr": expr_array}
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