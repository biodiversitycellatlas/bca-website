from typing import TextIO

from django.core.management import BaseCommand

from app.systemchecks.data import check_data_existence


class Command(BaseCommand):
    """
    Checks data existence for all datasets
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

        errors = check_data_existence()
        if errors:
            for error in errors:
                self.stdout.write(error.msg)
        else:
            self.stdout.write(self.style.SUCCESS("Successfully checked data"))
