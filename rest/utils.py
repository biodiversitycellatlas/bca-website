from django.db import connection
from app.utils import getDataset

def check_model_exists(model):
    return model._meta.db_table in connection.introspection.table_names()

def parse_species_dataset(value):
	dataset = getDataset(value)
	if not dataset:
		raise ValueError(f'Cannot find dataset for {value}')
	return dataset
