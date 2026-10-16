"""``wltk pivot`` - find other clients that requested the same URLs."""

import argparse
from collections import defaultdict

from ..logio import add_limit_argument, add_summary_arguments, emit_rows, read_fields
from .get_hostname import add_ip_argument, make_keep

NAME = "pivot"
HELP = "Find clients that requested the same URLs as a suspect"

EXAMPLES = 3


def run(args: argparse.Namespace) -> int:
    """Run the ``pivot`` tool and return an exit code."""
    keep = make_keep(args.ip)
    hosts_by_url: defaultdict[str, set[str]] = defaultdict(set)
    urls_by_host: defaultdict[str, set[str]] = defaultdict(set)
    suspect_urls: set[str] = set()
    for fields in read_fields(args.logfile):
        host, url = fields["hostname"] or "-", fields["url"] or "-"
        hosts_by_url[url].add(host)
        urls_by_host[host].add(url)
        if keep(fields):
            suspect_urls.add(url)

    # URLs requested by crowds (e.g. "/") would link everybody to the suspect.
    distinctive = {u for u in suspect_urls if len(hosts_by_url[u]) <= args.max_hosts}
    others = [
        (host, sorted(urls & distinctive))
        for host, urls in urls_by_host.items()
        if not keep({"hostname": host})
    ]
    ranked = sorted(
        (item for item in others if len(item[1]) >= args.min_shared),
        key=lambda item: (-len(item[1]), item[0]),
    )
    rows = [
        (host, len(shared), " ".join(shared[:EXAMPLES]))
        for host, shared in ranked[: args.limit]
    ]
    header = ("hostname", "shared_urls", "examples")
    return emit_rows(args, header, rows, empty="no related clients found")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``pivot`` tool."""
    add_summary_arguments(parser)
    add_ip_argument(parser, "suspect source IP, CIDR range or hostname")
    parser.add_argument(
        "--min-shared",
        type=int,
        default=1,
        metavar="N",
        help="clients must share at least N URLs with the suspect (default: 1)",
    )
    parser.add_argument(
        "--max-hosts",
        type=int,
        default=20,
        metavar="N",
        help="ignore URLs requested by more than N clients (default: 20)",
    )
    add_limit_argument(parser, "clients", default=20)
