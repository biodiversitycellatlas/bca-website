from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0014_add_mge_covering_index'),
    ]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS pg_trgm;"),
    ]
