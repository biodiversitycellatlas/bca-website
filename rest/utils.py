from django.db import connection

def check_model_exists(model):
    return model._meta.db_table in connection.introspection.table_names()

def parse_species_dataset(value):
	v = value.split('-')
	species = " ".join(v[0:2])
	if len(v) > 2:
		dataset = " ".join(v[2:])
	else:
		dataset = None
	return (species, dataset)