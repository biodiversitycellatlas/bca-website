from typing import TextIO

from django.core.management import BaseCommand

from app.systemchecks.cell_type_trees import check_cell_type_tree_consistency


class Command(BaseCommand):
    """
    Checks the consistency of cell type trees (Newick labels vs node rows)
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
        Cell type tree checks
        """
        errors = check_cell_type_tree_consistency()
        if not errors:
            self.stdout.write(self.style.SUCCESS("Successfully checked cell type trees"))
        else:
            self.stdout.write(self.style.ERROR("Problems with cell type trees"))
            for error in errors:
                self.stdout.write(error.msg)
