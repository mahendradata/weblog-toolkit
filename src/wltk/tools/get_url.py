"""``wltk get_url`` - keep the lines whose URL matches a regex."""

import argparse
import re
from urllib.parse import unquote

from ..logio import Fields, Keep, add_filter_arguments, run_filter

NAME = "get_url"
HELP = "Keep the lines whose URL matches a regex"


def make_keep(pattern: re.Pattern[str]) -> Keep:
    """Build a filter matching URLs where ``pattern`` is found.

    The URL is tested both as logged and percent-decoded, so ``../`` also finds
    ``%2e%2e%2f``.
    """

    def keep(fields: Fields) -> bool:
        url = fields["url"] or ""
        return bool(pattern.search(url) or pattern.search(unquote(url)))

    return keep


def run(args: argparse.Namespace) -> int:
    """Run the ``get_url`` tool and return an exit code."""
    return run_filter(args, make_keep(args.pattern))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``get_url`` tool."""
    add_filter_arguments(parser)
    parser.add_argument(
        "-u",
        "--url",
        dest="pattern",
        type=re.compile,
        required=True,
        metavar="REGEX",
        help="regular expression searched in the URL (e.g. 'wp-login|admin')",
    )
