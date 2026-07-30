import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0014_add_mge_covering_index"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpressionConservation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "conservation",
                    models.FloatField(help_text="Expression conservation score."),
                ),
                (
                    "is_one_to_one",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the ortholog pair is one-to-one.",
                    ),
                ),
                (
                    "dataset_a",
                    models.ForeignKey(
                        help_text="Dataset for the first gene.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conservations_as_a",
                        to="app.dataset",
                    ),
                ),
                (
                    "dataset_b",
                    models.ForeignKey(
                        help_text="Dataset for the second gene.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conservations_as_b",
                        to="app.dataset",
                    ),
                ),
                (
                    "gene_a",
                    models.ForeignKey(
                        help_text="First gene in the ortholog pair.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conservations_as_a",
                        to="app.gene",
                    ),
                ),
                (
                    "gene_b",
                    models.ForeignKey(
                        help_text="Second gene in the ortholog pair.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conservations_as_b",
                        to="app.gene",
                    ),
                ),
                (
                    "orthogroup",
                    models.ForeignKey(
                        help_text="Orthogroup the conservation belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conservations",
                        to="app.orthogroup",
                    ),
                ),
            ],
            options={
                "verbose_name": "Expression conservation score",
                "verbose_name_plural": "Expression conservation scores",
                "ordering": ["orthogroup"],
            },
        ),
        migrations.AddIndex(
            model_name="expressionconservation",
            index=models.Index(
                fields=["gene_a"], name="app_express_gene_a__a3dbef_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="expressionconservation",
            index=models.Index(
                fields=["gene_b"], name="app_express_gene_b__67cd7e_idx"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="expressionconservation",
            unique_together={("gene_a", "gene_b", "dataset_a", "dataset_b")},
        ),
    ]
