"""``wltk get_time`` - keep the lines inside a time window."""

import argparse
import sys
from datetime import datetime, tzinfo

from ..logio import Fields, Keep, add_filter_arguments, parse_time, run_filter

NAME = "get_time"
HELP = "Keep the lines inside a time window"


def make_keep(start: datetime | None, end: datetime | None) -> Keep:
    """Build a filter matching timestamps within ``start`` and ``end`` (inclusive).

    Bounds without a timezone are read in each log line's own timezone. Lines
    with an unreadable timestamp never match.
    """

    def keep(fields: Fields) -> bool:
        time = parse_time(fields["time"] or "")
        if time is None:
            return False
        low = _in_zone(start, time.tzinfo)
        high = _in_zone(end, time.tzinfo)
        return (low is None or time >= low) and (high is None or time <= high)

    return keep


def _in_zone(bound: datetime | None, zone: tzinfo | None) -> datetime | None:
    """Give a naive ``bound`` the timezone ``zone``; keep an aware one as is."""
    if bound is None or bound.tzinfo is not None:
        return bound
    return bound.replace(tzinfo=zone)


def run(args: argparse.Namespace) -> int:
    """Run the ``get_time`` tool and return an exit code."""
    if args.start is None and args.end is None:
        print("wltk: give at least one of --from / --to", file=sys.stderr)
        return 2
    return run_filter(args, make_keep(args.start, args.end))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``get_time`` tool."""
    add_filter_arguments(parser)
    parser.add_argument(
        "--from",
        dest="start",
        type=datetime.fromisoformat,
        metavar="TIME",
        help="earliest time, ISO 8601 (e.g. 2019-01-22T03:56:00+03:30)",
    )
    parser.add_argument(
        "--to",
        dest="end",
        type=datetime.fromisoformat,
        metavar="TIME",
        help="latest time, ISO 8601; a date alone means midnight",
    )
