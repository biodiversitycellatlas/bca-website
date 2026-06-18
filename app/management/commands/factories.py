import factory

from app.models import (
    Gene,
    Domain,
    GeneList,
    GeneModule,
    Orthogroup,
    Ortholog,
    Metacell,
    MetacellType,
    MetacellCount,
    MetacellGeneExpression,
    SingleCell,
)


class DomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Domain

    name = factory.Faker("word")


class GeneListFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GeneList

    name = factory.Faker("word")
    description = factory.Faker("sentence", nb_words=3, variable_nb_words=True)


class GeneModuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GeneModule

    name = factory.Faker("color_name")

    @factory.post_generation
    def genes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.genes.add(*extracted)


class GenesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Gene

    name = factory.LazyAttributeSequence(lambda obj, n: "%s__%03d" % (obj.species.common_name, n))
    description = factory.Faker("sentence", nb_words=3, variable_nb_words=True)

    @factory.post_generation
    def domains(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.domains.add(*extracted)

    @factory.post_generation
    def genelists(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.genelists.add(*extracted)


class OrthologFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ortholog


class OrthoGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Orthogroup

    name = factory.Faker("word")

    @factory.post_generation
    def genes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.genes.add(*extracted)


class MetaCellTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MetacellType

    name = factory.Iterator(
        ["Sperm", "Neuron", "Immune", "Gland", "Epidermis", "Fiber", "Precursor", "Muscle", "Gastrodermis"]
    )
    color = factory.Faker("color")


class MetacellFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Metacell

    name = factory.LazyAttributeSequence(lambda obj, n: str(n))
    type = factory.Iterator(MetacellType.objects.all())
    x = factory.Faker("random_int", min=-20, max=1200)
    y = factory.Faker("random_int", min=-20, max=1200)


class MetacellCountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MetacellCount

    cells = factory.Faker("random_int", min=0, max=200)
    umis = factory.Faker("random_int", min=10000, max=130000)
    metacell = factory.SubFactory(MetacellFactory, dataset=factory.SelfAttribute("..dataset"))


class MetacellGeneExpressionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MetacellGeneExpression

    umi_raw = factory.Faker("random_int", min=0, max=1000)
    umifrac = factory.Faker("pyfloat", min_value=0.00001, max_value=0.1)
    fold_change = factory.Faker("pyfloat", min_value=0.5, max_value=2050)


class SingleCellFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SingleCell

    name = factory.Faker("bothify", text="????????????-@", letters="ACTG")
    metacell = factory.Iterator(Metacell.objects.all())
