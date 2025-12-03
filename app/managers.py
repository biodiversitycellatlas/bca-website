from django.forms import model_to_dict
from django.shortcuts import get_object_or_404

from app.models import Dataset, Gene, DatasetFile, SingleCellGeneExpression
from app.utils import get_dataset, read_hdf


class ExpressionDataManager:
    """Creates SingleCellExpression models from data in HDF5."""

    def __init__(self, dataset: int, gene: int):
        dataset_id = get_dataset(dataset).id
        self.dataset = get_object_or_404(Dataset, pk=dataset_id)
        # self.dataset = get_object_or_404(Dataset, pk=dataset)
        self.gene = get_object_or_404(Gene, name=gene)

    def create_singlecellexpression_models(self):
        dataset_file = get_object_or_404(DatasetFile, dataset_id=self.dataset.pk)
        expression_dictionary = read_hdf(dataset_file.file.path, self.gene.name)
        result = []
        for row, key in enumerate(expression_dictionary, 1):
            scge = SingleCellGeneExpression()
            scge.id = row
            scge.gene = self.gene.name
            scge.dataset = self.dataset.slug
            scge.single_cell = key
            scge.umifrac = expression_dictionary[key]
            result.append(model_to_dict(scge))
        return result
