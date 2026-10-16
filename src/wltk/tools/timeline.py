"""``wltk timeline`` - what a client did, in order, split into sessions."""

import argparse
from datetime import datetime, timedelta

from ..logio import add_summary_arguments, emit_rows, read_timed, size_of
from .get_hostname import add_ip_argument, make_keep

NAME = "timeline"
HELP = "Chronological requests of given clients, in sessions"


def run(args: argparse.Namespace) -> int:
    """Run the ``timeline`` tool and return an exit code."""
    keep = make_keep(args.ip)
    events = sorted(
        ((time, fields) for time, fields in read_timed(args.logfile) if keep(fields)),
        key=lambda event: event[0],
    )
    gap = timedelta(minutes=args.gap)
    last_seen: dict[str, datetime] = {}
    session: dict[str, int] = {}
    rows = []
    for time, fields in events:
        host = fields["hostname"] or "-"
        if host not in last_seen or time - last_seen[host] > gap:
            session[host] = session.get(host, 0) + 1
        last_seen[host] = time
        rows.append(
            (
                host,
                session[host],
                time.isoformat(),
                fields["method"],
                fields["url"],
                fields["status"],
                size_of(fields),
            )
        )
    header = ("hostname", "session", "time", "method", "url", "status", "bytes")
    return emit_rows(args, header, rows, empty="no matching requests")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``timeline`` tool."""
    add_summary_arguments(parser)
    add_ip_argument(parser, "source IP, CIDR range or hostname to follow")
    parser.add_argument(
        "--gap",
        type=float,
        default=30,
        metavar="MINUTES",
        help="idle time that starts a new session (default: 30)",
    )
