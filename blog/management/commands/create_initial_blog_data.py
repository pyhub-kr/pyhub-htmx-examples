from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.factories import UserFactory
from blog.factories import CategoryFactory, TagFactory, PostFactory, CommentFactory
from blog.models import Category, Post, Tag, Comment


User = get_user_model()


class Command(BaseCommand):
    help = 'Generates fake data for blog app'

    def handle(self, *args, **options):
        self.stdout.write('Creating fake data...')

        # Create users if not exist
        if User.objects.all().exists() is False:
            UserFactory.create(
                username='admin',
                password='adminpassword',
                is_staff=True,
                is_superuser=True
            )
            UserFactory.create_batch(5)

        confirm = input('This will delete all Category, Tag, Post, Comment data. Do you want to proceed? [Y/n]: ').lower()
        if (not confirm) or confirm.startswith('y'):
            self.stdout.write('Deleting all Category, Tag, Post, Comment data...')
            Category.objects.all().delete()
            Tag.objects.all().delete()
            Post.objects.all().delete()
            Comment.objects.all().delete()
            self.stdout.write(self.style.WARNING('All existing Category, Tag, Post, Comment data have been deleted.'))
        else:
            self.stdout.write(self.style.ERROR('Operation cancelled.'))
            return

        # Generate Categories
        CategoryFactory.create_batch(100)
        self.stdout.write(self.style.SUCCESS(f'Created {Category.objects.count()} categories'))

        # Generate Tags
        TagFactory.create_batch(100)
        self.stdout.write(self.style.SUCCESS(f'Created {Tag.objects.count()} tags'))

        # Generate Posts
        PostFactory.create_batch(100)
        self.stdout.write(self.style.SUCCESS(f'Created {Post.objects.count()} posts'))

        # Generate Comments
        CommentFactory.create_batch(100)
        self.stdout.write(self.style.SUCCESS(f'Created {Comment.objects.count()} comments'))

        self.stdout.write(self.style.SUCCESS('Fake data generation completed!'))
