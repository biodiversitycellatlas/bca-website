from django.db import migrations, models


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction.
    atomic = False

    dependencies = [
        ("app", "0013_go_annotation"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Idempotent DB build: a no-op where the index already exists (e.g.
            # production, where it was created manually), and builds it
            # concurrently everywhere else (fresh dev/CI/test databases).
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "app_mge_dataset_gene_covering "
                        "ON app_metacellgeneexpression (dataset_id, gene_id) "
                        "INCLUDE (metacell_id, umi_raw, fold_change);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS "
                        "app_mge_dataset_gene_covering;"
                    ),
                ),
            ],
            # State only: keeps Django's model state in sync with the
            # ``Meta.indexes`` entry so ``makemigrations --check`` stays green.
            state_operations=[
                migrations.AddIndex(
                    model_name="metacellgeneexpression",
                    index=models.Index(
                        fields=["dataset", "gene"],
                        include=["metacell", "umi_raw", "fold_change"],
                        name="app_mge_dataset_gene_covering",
                    ),
                ),
            ],
        ),
    ]
