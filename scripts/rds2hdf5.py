from typing import Dict, List

import h5py
import numpy as np
from rds2py import parse_rds 
from rds2py.read_matrix import read_dgcmatrix
import scipy


def rds2hdf(rds_file: str, output_file:str) -> None:
    """ Transforms a gene expression matrix in RDS to HDF
    
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
        data = parse_rds(rds_file)
        wrapper = read_dgcmatrix(data)
        (genes, cells) = wrapper.dimnames
        matrix = wrapper.matrix 
        
        # computing umifrac values in place
        column_sums = matrix.sum(axis=0)
        row_indices, col_indices = matrix.nonzero()
        for i,j in zip(row_indices, col_indices):
            matrix[i,j] = 10000.0 * matrix[i,j] / column_sums[0,j]
 
        with h5py.File(output_file, "w") as root:
            root.create_dataset("cell_names", data=cells, dtype=h5py.string_dtype())
            for i, gene in enumerate(genes):
                row = matrix.getrow(i)
                (rows, columns) = row.nonzero()
                dataset = np.empty(shape=len(columns), dtype=[("c", np.int32), ("e", np.float32)])
                for p,j in enumerate(columns):
                    dataset[p] = (j, matrix[i,j])
                try:
                    root.create_dataset(gene, data=dataset)
                except():
                    print(f"gene {gene}")
    except(IOError):
        print("Problem opening the rds file or creating the hdf5 output")


def createPositionsDictionary(aList: np.typing.ArrayLike) -> Dict[int, str]:
    """ Creates a dictionary from positions to elements in the array  
        
        Args:
            aList: numpy array of strings (cell names)
        Returns: 
            dictionary e.g: { 0: "AAACG-1", 3:"CCTG-3"}
    
    """
    dictionary = {}
    for pos,value in enumerate(aList):        
        dictionary[pos] = str(value, encoding="ascii")
    return dictionary


def readfromhdf(hdf_file:str, gene:str) -> Dict[str, float]:
    """ Reads the expression values for a given gene from HDF5 file

        Args:
            hdf_file: path to the HDF5 file
            gene: a gene, e.g ("Spolac_c99997_g1")
        Returns:
            A dictionary of cell names to UMI frac expression values, e.g.
            {"AACTC-1": 1.462, "ACCG-1": 1.235}

    """
    with h5py.File(hdf_file, "r") as f:
        expressionValues = f.get(f"/{gene}")[:]
        cellnames = f.get(f"/cell_names")[:]
        cellsPositionsDict = createPositionsDictionary(cellnames)
        result = {}
        for elem in np.nditer(expressionValues, flags=["zerosize_ok"]):
            position = int(elem["c"])
            result[cellsPositionsDict[position]] = float(elem["e"])
        return result
