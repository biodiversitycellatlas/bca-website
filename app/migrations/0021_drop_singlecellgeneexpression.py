from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0020_rc_release_fixes')
    ]

    operations = [
        migrations.DeleteModel(
            name='SingleCellGeneExpression'
        )
    ]
