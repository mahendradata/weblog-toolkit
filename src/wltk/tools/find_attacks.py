"""``wltk find_attacks`` - flag requests that match known attack signatures."""

import argparse

from ..logio import add_summary_arguments, emit_rows, read_fields, run_filter
from ..signatures import ATTACK_CATEGORIES, classify

NAME = "find_attacks"
HELP = "Flag requests matching attack signatures (SQLi, XSS, traversal, ...)"


def run(args: argparse.Namespace) -> int:
    """Run the ``find_attacks`` tool and return an exit code."""
    wanted = set(args.category or ATTACK_CATEGORIES)

    if args.raw:
        return run_filter(args, lambda fields: bool(wanted & set(classify(fields))))

    rows = [
        (fields["time"], fields["hostname"], category, fields["status"], fields["url"])
        for fields in read_fields(args.logfile)
        for category in classify(fields)
        if category in wanted
    ]
    header = ("time", "hostname", "category", "status", "url")
    return emit_rows(args, header, rows, empty="no attack signatures found")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``find_attacks`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "-c",
        "--category",
        action="append",
        choices=ATTACK_CATEGORIES,
        help="only look for this category (repeatable; default: all)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="output the flagged log lines unchanged, to chain with other tools",
    )
