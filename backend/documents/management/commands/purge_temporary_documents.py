from django.core.management.base import BaseCommand
from documents.services.temporary_storage import purge_expired_documents


class Command(BaseCommand):
    help = 'Delete expired public-workflow documents and exports.'
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f'Deleted {purge_expired_documents()} expired document(s).'))
