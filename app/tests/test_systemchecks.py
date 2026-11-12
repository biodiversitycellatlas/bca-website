import os
import tempfile

from django.core.files import File as DjangoFile
from django.test import TestCase, override_settings

from app.apps import AppConfig
from app.models import (
    CellTypeTree,
    CellTypeTreeNode,
    Dataset,
    DatasetQualityControl,
    Gene,
    Metacell,
    MetacellCount,
    MetacellGeneExpression,
    MetacellType,
    QualityControl,
    SingleCell,
    Species,
    SpeciesFile,
)
from app.systemchecks.cell_type_trees import check_cell_type_tree_consistency
from app.systemchecks.data import check_data
from app.systemchecks.files import check_application_files
from app.systemchecks.metacellgenexpression import check_negative_umis
from app.systemchecks.metadata import check_metadata
from app.systemchecks.postgresql_tables import check_tables
from app.utils.newick import parse_newick_labels


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestFilesSystemCheck(TestCase):
    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(
            common_name="fileschecker", scientific_name="FileCheckerSp", description="F C Species"
        )
        test_file = os.path.join(os.path.dirname(__file__), "test_fixtures", "test-dmd-db.dmnd")
        with open(test_file, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(test_file))
            SpeciesFile.objects.get_or_create(species=species1, type="DIAMOND", defaults={"file": django_file})

    def test_execution(self):
        errors = check_application_files([AppConfig], deploy=True)
        assert len(errors) == 1
        assert errors[0].id == "bca.E001"


class TestMetacellGeneExpressionCheck(TestCase):
    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(
            common_name="metacellgeneexpcheck",
            scientific_name="metacellgeneexpcheck",
            description="metacellgeneexpcheck Species",
        )
        dataset1 = Dataset.objects.create(species=species1, name="mcgecheckdataset", description="mcgecheckdataset")
        gene1 = Gene.objects.create(species=species1, name="gene1", description="gene1")
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        meta1 = Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=1, y=1)
        MetacellGeneExpression.objects.create(
            dataset=dataset1, gene=gene1, metacell=meta1, umi_raw=-1, umifrac=1.41, fold_change=4
        )

    def test_execution(self):
        errors = check_negative_umis([AppConfig], deploy=True)
        assert len(errors) == 1
        assert errors[0].id == "bca.E002"


class TestPostgresTablesCheck(TestCase):
    @classmethod
    def setUpTestData(cls):
        speciesP = Species.objects.create(
            common_name="postgrescheck",
            scientific_name="postgrescheck",
            description="postgrescheck Species",
        )
        dataset1 = speciesP.datasets.create(name="psqlcheckdataset", description="psqlcheckdataset")
        gene1 = speciesP.genes.create(name="geneP", description="geneP")
        gm = dataset1.gene_modules.create(name="psql")
        gm.membership.create(membership_score=4.1, gene=gene1)

    # In test mode there are several empty tables.
    # Looking only for table 'genemodule':
    def test_execution(self):
        errors = check_tables([AppConfig], deploy=True)
        for error in errors:
            if error.obj == "genemodule":
                assert error.id == "bca.E003"


class TestMetadataCheck(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.species = Species.objects.create(
            common_name="metadatacheck",
            scientific_name="metadatacheck",
            description="metadatacheck Species",
        )
        cls.dataset = Dataset.objects.create(
            species=cls.species, name="metadatacheckdataset", description="metadatacheckdataset"
        )
        quality_control = QualityControl.objects.create(
            type="Mapping", name="Number of eyes", description="number of eyes"
        )
        DatasetQualityControl.objects.create(
            dataset=cls.dataset,
            metric=quality_control,
            value="two",
        )

    def test_execution(self):
        errors = check_metadata([AppConfig], deploy=True)
        assert len(errors) == 4

    def test_execution_without_errors(self):
        type1 = MetacellType.objects.create(name="type1", dataset=self.dataset)
        metacell1 = Metacell.objects.create(name="meta1", dataset=self.dataset, type=type1, x=1, y=1)
        SingleCell.objects.create(name="singleCell", dataset=self.dataset, metacell=metacell1)
        MetacellCount.objects.create(dataset=self.dataset, metacell=metacell1, cells=20, umis=200)
        Gene.objects.create(name="metagene1", species=self.species)
        errors = check_metadata([AppConfig], deploy=True)
        assert len(errors) == 0


class TestDataCheck(TestCase):
    def test_execution_without_errors(self):
        errors = check_metadata([AppConfig], deploy=True)
        assert len(errors) == 0

    def test_execution_with_errors(self):
        human = Species.objects.create(
            common_name="datahuman",
            scientific_name="data Homo",
            description="human data test",
        )
        Dataset.objects.create(name="Data Homo - adult", description="random human", species=human)
        errors = check_data([AppConfig], deploy=True)
        assert len(errors) == 17


class TestNewickParser(TestCase):
    def test_simple_tree(self):
        assert parse_newick_labels("(a,b)c;") == {"a", "b", "c"}

    def test_nested_tree(self):
        assert parse_newick_labels("((a,b)c,(d,e)f)root;") == {"a", "b", "c", "d", "e", "f", "root"}

    def test_quoted_labels(self):
        assert parse_newick_labels('("Node 2",b)root;') == {"Node 2", "b", "root"}

    def test_branch_lengths(self):
        assert parse_newick_labels("(a:0.1,b:0.2)c:1.0;") == {"a", "b", "c"}

    def test_comments(self):
        assert parse_newick_labels("(a[&&NHX:Id=1],b)c;") == {"a", "b", "c"}

    def test_single_node(self):
        assert parse_newick_labels("root;") == {"root"}

    def test_unrooted_tree(self):
        assert parse_newick_labels("a,b,c;") == {"a", "b", "c"}

    def test_invalid_newick(self):
        with self.assertRaises(ValueError):
            parse_newick_labels("(a,b;")
        with self.assertRaises(ValueError):
            parse_newick_labels("(a,b")
        with self.assertRaises(ValueError):
            parse_newick_labels("a)b;")


class TestCellTypeTreeCheck(TestCase):
    @classmethod
    def setUpTestData(cls):
        species = Species.objects.create(
            common_name="treecheck", scientific_name="TreeCheckSp", description="tree check species"
        )
        dataset = Dataset.objects.create(species=species, name="DTreeCheck", description="tree check dataset")
        cls.tree = CellTypeTree.objects.create(dataset=dataset, newick="((a,b)c,d)root;")

    def test_consistent_tree(self):
        for node in ["a", "b", "c", "d", "root"]:
            CellTypeTreeNode.objects.create(tree=self.tree, node=node)
        assert check_cell_type_tree_consistency() == []

    def test_newick_label_without_node_row(self):
        CellTypeTreeNode.objects.create(tree=self.tree, node="root")
        errors = check_cell_type_tree_consistency()
        assert len(errors) == 4
        assert all(e.id == "bca.E006" for e in errors)

    def test_node_row_not_in_newick(self):
        for node in ["a", "b", "c", "d", "root", "extra"]:
            CellTypeTreeNode.objects.create(tree=self.tree, node=node)
        errors = check_cell_type_tree_consistency()
        assert len(errors) == 1
        assert "extra" in errors[0].msg

    def test_invalid_newick(self):
        CellTypeTree.objects.create(dataset=self.tree.dataset, newick="(a,b;")
        errors = check_cell_type_tree_consistency()
        assert any("invalid Newick" in e.msg for e in errors)

    def test_empty_newick(self):
        CellTypeTree.objects.create(dataset=self.tree.dataset, newick="   ")
        errors = check_cell_type_tree_consistency()
        assert any("empty" in e.msg for e in errors)
