import random

from factory import Iterator, LazyAttribute, LazyFunction, SubFactory, post_generation
from factory.django import DjangoModelFactory
from faker import Faker

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from blog.models import Category, Tag, Post, Comment


User = get_user_model()


fake = Faker()


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = LazyFunction(lambda: fake.unique.word())
    slug = LazyAttribute(lambda obj: slugify(obj.name))


class TagFactory(DjangoModelFactory):
    class Meta:
        model = Tag

    name = LazyFunction(lambda: fake.unique.word())
    slug = LazyAttribute(lambda obj: slugify(obj.name))


class PostFactory(DjangoModelFactory):
    class Meta:
        model = Post

    title = LazyFunction(fake.unique.sentence)
    slug = LazyAttribute(lambda obj: slugify(obj.title))
    content = LazyFunction(fake.paragraphs)
    author = Iterator(User.objects.all())
    category = SubFactory(CategoryFactory)

    @post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            for _ in range(random.randint(1, 5)):
                self.tags.add(TagFactory())


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = Comment

    content = LazyFunction(fake.paragraph)
    author = Iterator(User.objects.all())
    post = Iterator(Post.objects.all())
