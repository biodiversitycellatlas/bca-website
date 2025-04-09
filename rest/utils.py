from django.db import connection

def check_model_exists(model):
    return model._meta.db_table in connection.introspection.table_names()
