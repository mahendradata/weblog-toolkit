"""``wltk get_status`` - keep the lines with given HTTP status codes."""

import argparse
import re
from collections.abc import Sequence

from ..logio import Fields, Keep, add_filter_arguments, run_filter

NAME = "get_status"
HELP = "Keep the lines with given HTTP status codes or classes"

STATUS = re.compile(r"\d{3}|\dxx", re.IGNORECASE)


def make_keep(statuses: Sequence[str]) -> Keep:
    """Build a filter matching exact codes (``404``) or classes (``4xx``)."""
    wanted = {status.lower() for status in statuses}

    def keep(fields: Fields) -> bool:
        code = fields["status"] or ""
        return code in wanted or f"{code[:1]}xx" in wanted

    return keep


def run(args: argparse.Namespace) -> int:
    """Run the ``get_status`` tool and return an exit code."""
    return run_filter(args, make_keep(args.status))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``get_status`` tool."""
    add_filter_arguments(parser)
    parser.add_argument(
        "-s",
        "--status",
        action="append",
        required=True,
        type=status_type,
        metavar="CODE",
        help="status code (404) or class (4xx) to keep (repeatable)",
    )


def status_type(value: str) -> str:
    """Validate a status argument such as ``404`` or ``4xx``."""
    if not STATUS.fullmatch(value):
        raise argparse.ArgumentTypeError(f"invalid status '{value}' (use 404 or 4xx)")
    return value
