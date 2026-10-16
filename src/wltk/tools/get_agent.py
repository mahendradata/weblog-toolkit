"""``wltk get_agent`` - keep the lines whose User-Agent matches a regex."""

import argparse
import re

from ..logio import Fields, Keep, add_filter_arguments, run_filter

NAME = "get_agent"
HELP = "Keep the lines whose User-Agent matches a regex"


def make_keep(pattern: re.Pattern[str]) -> Keep:
    """Build a filter matching User-Agents where ``pattern`` is found.

    Lines without a User-Agent field (Common Log Format) never match.
    """

    def keep(fields: Fields) -> bool:
        agent = fields.get("user_agent")
        return agent is not None and bool(pattern.search(agent))

    return keep


def run(args: argparse.Namespace) -> int:
    """Run the ``get_agent`` tool and return an exit code."""
    return run_filter(args, make_keep(args.pattern))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``get_agent`` tool."""
    add_filter_arguments(parser)
    parser.add_argument(
        "-a",
        "--agent",
        dest="pattern",
        type=_ignore_case,
        required=True,
        metavar="REGEX",
        help="case-insensitive regex searched in the User-Agent (e.g. 'sqlmap|curl')",
    )


def _ignore_case(value: str) -> re.Pattern[str]:
    """Compile ``value`` as a case-insensitive regular expression."""
    return re.compile(value, re.IGNORECASE)
