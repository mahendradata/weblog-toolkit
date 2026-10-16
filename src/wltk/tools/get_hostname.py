"""``wltk get_hostname`` - keep the lines of given source IPs or hostnames."""

import argparse
import ipaddress
from collections.abc import Sequence

from ..logio import Fields, Keep, add_filter_arguments, run_filter

NAME = "get_hostname"
HELP = "Keep the lines of given source IPs, CIDR ranges or hostnames"


def make_keep(sources: Sequence[str]) -> Keep:
    """Build a filter matching hostnames equal to, or inside, any of ``sources``.

    Each source is an IP address, a CIDR range (``10.0.0.0/24``) or a plain
    hostname. Anything that is not a valid network is matched as a literal hostname.
    """
    networks = []
    names = set()
    for source in sources:
        try:
            networks.append(ipaddress.ip_network(source, strict=False))
        except ValueError:
            names.add(source)

    def keep(fields: Fields) -> bool:
        host = fields["hostname"] or ""
        if host in names:
            return True
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return False
        return any(address in network for network in networks)

    return keep


def run(args: argparse.Namespace) -> int:
    """Run the ``get_hostname`` tool and return an exit code."""
    return run_filter(args, make_keep(args.ip))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``get_hostname`` tool."""
    add_filter_arguments(parser)
    add_ip_argument(parser, "source IP, CIDR range or hostname to keep")


def add_ip_argument(
    parser: argparse.ArgumentParser, what: str, required: bool = True
) -> None:
    """Add the repeatable ``-i/--ip`` argument, used by every per-client tool."""
    parser.add_argument(
        "-i",
        "--ip",
        action="append",
        required=required,
        metavar="IP",
        help=f"{what} (repeatable)",
    )
