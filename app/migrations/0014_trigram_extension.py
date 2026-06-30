from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0013_go_annotation'),
    ]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS pg_trgm;"),
    ]
