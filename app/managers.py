from django.forms import model_to_dict
from django.shortcuts import get_object_or_404

from app.models import Dataset, Gene, DatasetFile, SingleCellGeneExpression
from app.utils import get_dataset, read_hdf


class ExpressionDataManager:
    """Creates SingleCellExpression models from data in HDF5."""

    def __init__(self, dataset: int, gene: int):
        dataset_id = get_dataset(dataset).id
        self.dataset = get_object_or_404(Dataset, pk=dataset_id)
        self.gene = get_object_or_404(Gene, name=gene)
        dataset_file = get_object_or_404(DatasetFile, dataset_id=self.dataset.pk)
        self.expression_dictionary = read_hdf(dataset_file.file.path, self.gene.name)

    def get_expression_dictionary(self):
        return self.expression_dictionary

    def create_singlecellexpression_models(self):
        result = []
        for row, key in enumerate(self.expression_dictionary, 1):
            scge = SingleCellGeneExpression()
            scge.id = row
            scge.gene = self.gene.name
            scge.dataset = self.dataset.slug
            scge.single_cell = key
            scge.umifrac = self.expression_dictionary[key]
            result.append(model_to_dict(scge))
        return result
