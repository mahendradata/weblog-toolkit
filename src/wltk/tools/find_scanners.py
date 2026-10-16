"""``wltk find_scanners`` - spot clients probing the site for vulnerable pages."""

import argparse
from collections import defaultdict
from dataclasses import dataclass, field

from ..logio import add_summary_arguments, emit_rows, read_fields
from ..signatures import SCANNER_AGENTS

NAME = "find_scanners"
HELP = "Find clients with many 404s or a known scanner User-Agent"


@dataclass
class Client:
    """What one client did: requests, distinct URLs, 404s and scanner agent use."""

    requests: int = 0
    urls: set[str] = field(default_factory=set)
    not_found: int = 0
    scanner_agent: bool = False


def run(args: argparse.Namespace) -> int:
    """Run the ``find_scanners`` tool and return an exit code."""
    clients: defaultdict[str, Client] = defaultdict(Client)
    for fields in read_fields(args.logfile):
        client = clients[fields["hostname"] or "-"]
        client.requests += 1
        client.urls.add(fields["url"] or "-")
        client.not_found += fields["status"] == "404"
        client.scanner_agent |= bool(SCANNER_AGENTS.search(fields["user_agent"] or ""))

    flagged = sorted(
        ((host, c) for host, c in clients.items() if _is_scanner(c, args.min_404)),
        key=lambda item: (-item[1].not_found, item[0]),
    )
    rows = [
        (host, c.requests, len(c.urls), c.not_found, "yes" if c.scanner_agent else "no")
        for host, c in flagged
    ]
    header = ("hostname", "requests", "distinct_urls", "not_found", "scanner_agent")
    return emit_rows(args, header, rows, empty="no scanners found")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``find_scanners`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "--min-404",
        type=int,
        default=20,
        metavar="N",
        help="flag clients with at least N 404 responses (default: 20)",
    )


def _is_scanner(client: Client, min_404: int) -> bool:
    """Tell whether a client probed too many missing pages or used a scanner."""
    return client.not_found >= min_404 or client.scanner_agent
