"""``wltk top`` - rank the most frequent values of a log field."""

import argparse

from ..logio import (
    add_limit_argument,
    add_summary_arguments,
    emit_rows,
    ranked_rows,
    read_fields,
    tally,
)

NAME = "top"
HELP = "Most frequent values of a field, by requests or bytes"

BY_CHOICES = ["hostname", "url", "user_agent", "referer", "status", "method", "userid"]


def run(args: argparse.Namespace) -> int:
    """Run the ``top`` tool and return an exit code."""
    totals = tally(read_fields(args.logfile), args.by, args.weight)
    rows = ranked_rows(totals, args.limit)
    return emit_rows(args, (args.weight, "percent", args.by), rows)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``top`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "-b",
        "--by",
        choices=BY_CHOICES,
        default="hostname",
        help="field to rank (default: hostname)",
    )
    parser.add_argument(
        "-w",
        "--weight",
        choices=["count", "bytes"],
        default="count",
        help="rank by number of requests or by bytes sent (default: count)",
    )
    add_limit_argument(parser, "rows", default=10)
