"""``wltk find_errors`` - spot bursts of server errors."""

import argparse
from collections import Counter, defaultdict

from ..logio import INTERVALS, add_summary_arguments, emit_rows, parse_time, read_fields
from .get_status import make_keep, status_type

NAME = "find_errors"
HELP = "Find time intervals with bursts of server errors"


def run(args: argparse.Namespace) -> int:
    """Run the ``find_errors`` tool and return an exit code."""
    keep = make_keep(args.status or ["5xx"])
    urls: defaultdict[str, Counter[str]] = defaultdict(Counter)
    clients: defaultdict[str, set[str]] = defaultdict(set)
    for fields in read_fields(args.logfile):
        time = parse_time(fields["time"] or "")
        if time is None or not keep(fields):
            continue
        period = time.strftime(INTERVALS[args.interval])
        urls[period][fields["url"] or "-"] += 1
        clients[period].add(fields["hostname"] or "-")

    rows = [
        (period, counts.total(), len(clients[period]), counts.most_common(1)[0][0])
        for period, counts in sorted(urls.items())
        if counts.total() >= args.min
    ]
    header = (args.interval, "errors", "clients", "top_url")
    return emit_rows(args, header, rows, empty="no error bursts found")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``find_errors`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "-s",
        "--status",
        action="append",
        type=status_type,
        metavar="CODE",
        help="status code or class counted as an error (repeatable; default: 5xx)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        choices=list(INTERVALS),
        default="minute",
        help="size of the time buckets (default: minute)",
    )
    parser.add_argument(
        "--min",
        type=int,
        default=10,
        metavar="N",
        help="only report intervals with at least N errors (default: 10)",
    )
