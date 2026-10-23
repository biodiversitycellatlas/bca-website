from typing import TextIO

from django.core.management import BaseCommand

from app.management.metadata_existence import check_metadata_existence


class Command(BaseCommand):
    """
    Checks the existence of metadata in all datasets
    """

    def __init__(
        self,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        no_color: bool = False,
        force_color: bool = False,
    ):
        super().__init__(stdout, stderr, no_color, force_color)

    def handle(self, *args, **options):
        """
        Metadata checks
        """
        errors = check_metadata_existence()
        if not errors:
            self.stdout.write(self.style.SUCCESS("Successfully checked metadata"))
        else:
            self.stdout.write(self.style.SUCCESS("Problems with metadata"))
            for error in errors:
                self.stdout.write(error.msg)
