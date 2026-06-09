from random import randint, random

import factory

from app.models import (
    Gene,
    Domain,
    GeneList,
    GeneCorrelation,
    GeneModule,
    Orthogroup,
    Ortholog,
    Metacell,
    MetacellType,
    MetacellCount,
)


class DomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Domain

    name = factory.Faker("word")


class GeneCorrelationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GeneCorrelation


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

    name = factory.LazyAttributeSequence(lambda obj, n: "metacell__%03d" % n)
    type = factory.Iterator(MetacellType.objects.all())
    x = random()
    y = random()


class MetacellCountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MetacellCount

    cells = randint(1, 200)
    umis = randint(10000, 130000)
    metacell = factory.SubFactory(MetacellFactory, dataset=factory.SelfAttribute("..dataset"))
