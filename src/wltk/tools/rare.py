"""``wltk rare`` - list the least frequent values of a log field."""

import argparse

from ..logio import (
    add_limit_argument,
    add_summary_arguments,
    emit_rows,
    ranked_rows,
    read_fields,
    tally,
)
from .top import BY_CHOICES

NAME = "rare"
HELP = "Least frequent values of a field"


def run(args: argparse.Namespace) -> int:
    """Run the ``rare`` tool and return an exit code."""
    totals = tally(read_fields(args.logfile), args.by)
    rows = ranked_rows(totals, args.limit, rarest=True)
    return emit_rows(args, ("count", "percent", args.by), rows)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``rare`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "-b",
        "--by",
        choices=BY_CHOICES,
        default="url",
        help="field to rank (default: url)",
    )
    add_limit_argument(parser, "rows", default=10)
