from django.core import checks
from django.core.checks import Error, register

from app.models import CellTypeTree, CellTypeTreeNode
from app.utils.newick import parse_newick_labels


@register(checks.Tags.files, deploy=True)
def check_cell_type_trees(app_configs, **kwargs) -> list[Error]:
    return check_cell_type_tree_consistency()


def check_cell_type_tree_consistency() -> list[Error]:
    """Checks that Newick node labels match cell type tree node rows"""

    errors = []
    for tree in CellTypeTree.objects.all():
        if not tree.newick.strip():
            errors.append(
                Error(
                    msg=f"Tree {tree}: the Newick string is empty",
                    hint="cell type tree",
                    obj=tree,
                    id="bca.E006",
                )
            )
            continue

        try:
            labels = parse_newick_labels(tree.newick)
        except ValueError as e:
            errors.append(
                Error(
                    msg=f"Tree {tree}: invalid Newick string: {e}",
                    hint="cell type tree",
                    obj=tree,
                    id="bca.E006",
                )
            )
            continue

        node_names = set(CellTypeTreeNode.objects.filter(tree=tree).values_list("node", flat=True))

        for label in sorted(labels - node_names):
            errors.append(
                Error(
                    msg=f"Tree {tree}: Newick node {label} has no cell type tree node row",
                    hint="cell type tree",
                    obj=tree,
                    id="bca.E006",
                )
            )
        for name in sorted(node_names - labels):
            errors.append(
                Error(
                    msg=f"Tree {tree}: cell type tree node {name} is not in the Newick string",
                    hint="cell type tree",
                    obj=tree,
                    id="bca.E006",
                )
            )
    return errors
