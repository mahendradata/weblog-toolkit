"""``wltk get_method`` - keep the lines with given HTTP methods."""

import argparse
from collections.abc import Sequence

from ..logio import Fields, Keep, add_filter_arguments, run_filter

NAME = "get_method"
HELP = "Keep the lines with given HTTP methods"


def make_keep(methods: Sequence[str]) -> Keep:
    """Build a filter matching any of ``methods`` (case-insensitive)."""
    wanted = {method.upper() for method in methods}

    def keep(fields: Fields) -> bool:
        return (fields["method"] or "").upper() in wanted

    return keep


def run(args: argparse.Namespace) -> int:
    """Run the ``get_method`` tool and return an exit code."""
    return run_filter(args, make_keep(args.method))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``get_method`` tool."""
    add_filter_arguments(parser)
    parser.add_argument(
        "-m",
        "--method",
        action="append",
        required=True,
        metavar="METHOD",
        help="HTTP method to keep, e.g. POST (repeatable)",
    )
