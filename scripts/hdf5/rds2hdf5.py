"""Conversion of UMI matrices from an RDS file to UMI fractions
in a HDF5 file optimized for fast gene retrieval
"""

from typing import Dict

import h5py
import numpy as np
import rds2py
from rds2py.read_matrix import read_dgcmatrix

# pylint: disable=unused-import
import scipy  # noqa


def read_matrix(rds_file: str):
    """Reads a sparse matrix (dgCMatrix) with UMI raw counts in an RDS file

    Args:
        rds_file: path to input RDS file
    Returns:
        Tuple with (genes, cell names, scipy matrix)
    """
    data = rds2py.parse_rds(rds_file)
    wrapper = read_dgcmatrix(data)
    (genes, cells) = wrapper.dimnames
    matrix = wrapper.matrix
    return (genes, cells, matrix)


def compute_umifractions(matrix):
    """Computes umifrac values in place"""
    column_sums = matrix.sum(axis=0)
    (row_indices, col_indices) = matrix.nonzero()
    for i, j in zip(row_indices, col_indices):
        matrix[i, j] = 10000.0 * matrix[i, j] / column_sums[0, j]


def rds2hdf(rds_file: str, output_file: str) -> None:
    """Transforms a gene expression matrix in RDS to HDF

    Assumption:
        the rds_file contains *one* sparse CSC matrix of expression values
        the columns are indexed by the different cells in the dataset
        the labeled index for the rows is the set of genes in the dataset

    Args:
        rds_file: path to RDS file
        output_file: path to output (hdf) file

    Side effect:
        Creates an hdf5 file in location output_file.
        The file has a dataset cell_names and datasets named after each gene
        cell_names is an array of names
        Each gene dataset is an array of pairs (pos, expressionValue)
        The integer pos points to the position of the cell name in the array cell_names

    Import requirements: pandas rds2py *scipy (or read_dgcmatrix fails)*
    Dependencies: {rds2py scipy}
    """
    try:
        (genes, cells, matrix) = read_matrix(rds_file)
    except IOError:
        print("Problem opening the RDS file")
    compute_umifractions(matrix)
    with h5py.File(output_file, "w") as root:
        root.create_dataset("cell_names", data=cells, dtype=h5py.string_dtype())
        for i, gene in enumerate(genes):
            row = matrix.getrow(i)
            (_, columns) = row.nonzero()
            dataset = np.empty(shape=len(columns), dtype=[("c", np.int32), ("e", np.float32)])
            if columns.size > 0:
                for p, j in enumerate(columns):
                    dataset[p] = (j, matrix[i, j])
                try:
                    root.create_dataset(gene, data=dataset)
                except ():
                    print(f"duplicated gene {gene}")


def create_positions_dictionary(a_list: np.typing.ArrayLike) -> Dict[int, str]:
    """Creates a dictionary from positions to elements in the array

    Args:
        a_list: numpy array of strings (cell names)
    Returns:
        dictionary e.g: { 0: "AAACG-1", 3:"CCTG-3"}
    """
    dictionary = {}
    for pos, value in enumerate(a_list):
        dictionary[pos] = str(value, encoding="ascii")
    return dictionary


def read_from_hdf(hdf_file: str, gene: str) -> Dict[str, float]:
    """Reads the expression values for a given gene from HDF5 file

    Args:
        hdf_file: path to the HDF5 file
        gene: a gene, e.g ("Spolac_c99997_g1")
    Returns:
        A dictionary of cell names to UMI frac expression values, e.g.
        {"AACTC-1": 1.462, "ACCG-1": 1.235}

    """
    with h5py.File(hdf_file, "r") as f:
        expression_values = f.get(f"/{gene}", default=np.empty(0))[:]
        cell_names = f.get("/cell_names")[:]
        cell_positions_dict = create_positions_dictionary(cell_names)
        result = {}
        for elem in np.nditer(expression_values, flags=["zerosize_ok"]):
            position = int(elem["c"])
            result[cell_positions_dict[position]] = float(elem["e"])
        return result
