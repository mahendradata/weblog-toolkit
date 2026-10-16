"""``wltk first_last`` - when each client was first and last seen."""

import argparse
from dataclasses import dataclass
from datetime import datetime

from ..logio import add_limit_argument, add_summary_arguments, emit_rows, read_timed
from .get_hostname import add_ip_argument, make_keep

NAME = "first_last"
HELP = "When each client was first and last seen"


@dataclass
class Span:
    """First and last request time of a client, and its request count."""

    first: datetime
    last: datetime
    requests: int = 0


def run(args: argparse.Namespace) -> int:
    """Run the ``first_last`` tool and return an exit code."""
    keep = make_keep(args.ip) if args.ip else (lambda _: True)
    spans: dict[str, Span] = {}
    for time, fields in read_timed(args.logfile):
        if not keep(fields):
            continue
        span = spans.setdefault(fields["hostname"] or "-", Span(time, time))
        span.first = min(span.first, time)
        span.last = max(span.last, time)
        span.requests += 1

    ordered = sorted(spans.items(), key=lambda item: (item[1].first, item[0]))
    rows = [
        (
            host,
            s.first.isoformat(),
            s.last.isoformat(),
            round((s.last - s.first).total_seconds() / 60, 1),
            s.requests,
        )
        for host, s in ordered[: args.limit]
    ]
    header = ("hostname", "first_seen", "last_seen", "minutes", "requests")
    return emit_rows(args, header, rows, empty="no matching requests")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``first_last`` tool."""
    add_summary_arguments(parser)
    add_ip_argument(parser, "only this IP, CIDR range or hostname", required=False)
    add_limit_argument(parser, "clients")
