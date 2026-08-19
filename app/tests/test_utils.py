"""Test app utility functions."""

from django.test import TestCase

from app.models import MetacellTypeSimilarity, Orthogroup, Species
from app.utils import get_compare_dataset_dict, get_dataset_dict, get_species_dict


class SpeciesDictTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.species = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.dataset = cls.species.datasets.create(name="adult")
        cls.species.meta_set.create(key="species", value="Mus musculus")
        cls.species.meta_set.create(key="phylum", value="Chordata")
        cls.species.meta_set.create(key="kingdom", value="Animalia")

    def test_phylum_searchable_in_dataset_dict(self):
        dataset_dict = get_dataset_dict()
        meta = dataset_dict["Chordata"][0]["meta"]
        assert "Chordata" in meta
        assert "Animalia" in meta
        assert "Mus musculus" not in meta

    def test_phylum_searchable_in_species_dict(self):
        species_dict = get_species_dict()
        meta = species_dict["Chordata"][0]["meta"]
        assert "Chordata" in meta
        assert "Animalia" in meta
        assert "Mus musculus" not in meta


class CompareDatasetDictTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Datasets with both SAMap and shared gene module orthogroups
        cls.mouse = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.human = Species.objects.create(scientific_name="Homo sapiens", common_name="human")
        cls.chimp = Species.objects.create(scientific_name="Pan troglodytes", common_name="chimp")

        cls.mouse_dataset = cls.mouse.datasets.create(name="adult")
        cls.human_dataset = cls.human.datasets.create(name="fetal")
        cls.chimp_dataset = cls.chimp.datasets.create(name="adult")
        cls.baby_mouse = cls.mouse.datasets.create(name="baby")

        # SAMap data between mouse and human datasets only
        t1 = cls.mouse_dataset.metacell_types.create(name="cell1")
        t2 = cls.human_dataset.metacell_types.create(name="cell2")
        MetacellTypeSimilarity.objects.create(metacelltype=t1, metacelltype2=t2, samap_score=0.8)

        # Genes and shared orthogroups
        og = Orthogroup.objects.create(name="OG1")
        g_mouse = cls.mouse.genes.create(name="Gene1")
        g_human = cls.human.genes.create(name="Gene2")
        g_chimp = cls.chimp.genes.create(name="Gene3")
        cls.mouse.orthologs.create(orthogroup=og, gene=g_mouse)
        cls.human.orthologs.create(orthogroup=og, gene=g_human)
        cls.chimp.orthologs.create(orthogroup=og, gene=g_chimp)

        # Gene modules containing ortholog-mapped genes
        cls.mouse_dataset.gene_modules.create(name="blue").genes.add(g_mouse)
        cls.human_dataset.gene_modules.create(name="blue").genes.add(g_human)
        cls.chimp_dataset.gene_modules.create(name="blue").genes.add(g_chimp)

    @classmethod
    def datasets(cls, dict_):
        return {elem["dataset"] for elems in dict_.values() for elem in elems}

    def test_includes_datasets_with_samap_and_module_data(self):
        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert self.human_dataset in self.datasets(dict_)

    def test_excludes_current_dataset_and_same_species(self):
        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert self.mouse_dataset not in self.datasets(dict_)
        assert self.baby_mouse not in self.datasets(dict_)

    def test_includes_datasets_with_module_orthogroups_only(self):
        # Chimp shares an orthogroup with mouse but has no SAMap data
        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert self.chimp_dataset in self.datasets(dict_)

    def test_includes_datasets_with_samap_only(self):
        # Dataset with SAMap data but no ortholog-mapped gene modules
        shark = Species.objects.create(scientific_name="Lamna nasus", common_name="shark")
        shark_dataset = shark.datasets.create(name="adult")
        t1 = self.mouse_dataset.metacell_types.create(name="cell3")
        t2 = shark_dataset.metacell_types.create(name="cell4")
        MetacellTypeSimilarity.objects.create(metacelltype=t1, metacelltype2=t2, samap_score=0.5)

        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert shark_dataset in self.datasets(dict_)

    def test_excludes_datasets_without_comparison_data(self):
        # Create an isolated species with no SAMap data or shared orthogroups
        snail = Species.objects.create(scientific_name="Cornu aspersum", common_name="snail")
        snail_dataset = snail.datasets.create(name="adult")
        assert snail_dataset not in self.datasets(get_compare_dataset_dict(self.mouse_dataset))
        assert get_compare_dataset_dict(snail_dataset) == {}
        assert get_compare_dataset_dict(None) == {}
