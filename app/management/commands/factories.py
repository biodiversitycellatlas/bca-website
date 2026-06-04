import factory

from app.models import Gene


class GenesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Gene

    name = factory.LazyAttributeSequence(lambda obj, n: "%s__%03d" % (obj.species.common_name, n))
    description = factory.Faker("sentence", nb_words=3, variable_nb_words=True)
