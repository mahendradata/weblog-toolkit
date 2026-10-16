"""``wltk find_bruteforce`` - spot repeated login attempts and possible break-ins."""

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass

from ..logio import add_summary_arguments, emit_rows, read_fields

NAME = "find_bruteforce"
HELP = "Find clients hammering login URLs, or logging in after failures"

LOGIN_URL = r"login|signin|sign-in|auth|admin|xmlrpc|account"


@dataclass
class Client:
    """Login attempts of one client, in log order."""

    attempts: int = 0
    failures: int = 0
    successes: int = 0
    break_in: bool = False


def run(args: argparse.Namespace) -> int:
    """Run the ``find_bruteforce`` tool and return an exit code."""
    clients: defaultdict[str, Client] = defaultdict(Client)
    for fields in read_fields(args.logfile):
        if fields["method"] != "POST" or not args.url.search(fields["url"] or ""):
            continue
        client = clients[fields["hostname"] or "-"]
        client.attempts += 1
        if int(fields["status"] or 0) in args.fail_status:
            client.failures += 1
        else:
            client.successes += 1
            client.break_in |= client.failures >= args.min_failures

    flagged = sorted(
        ((host, c) for host, c in clients.items() if _is_suspect(c, args.min_attempts)),
        key=lambda item: (-item[1].failures, -item[1].attempts, item[0]),
    )
    rows = [
        (host, c.attempts, c.failures, c.successes, "yes" if c.break_in else "no")
        for host, c in flagged
    ]
    header = ("hostname", "attempts", "failures", "successes", "success_after_failures")
    return emit_rows(args, header, rows, empty="no brute-force activity found")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``find_bruteforce`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "-u",
        "--url",
        type=lambda value: re.compile(value, re.IGNORECASE),
        default=re.compile(LOGIN_URL, re.IGNORECASE),
        metavar="REGEX",
        help=f"URLs that count as login pages (default: '{LOGIN_URL}')",
    )
    parser.add_argument(
        "--fail-status",
        type=_status_list,
        default=[401, 403],
        metavar="CODES",
        help="comma-separated status codes meaning a failed login (default: 401,403)",
    )
    parser.add_argument(
        "--min-attempts",
        type=int,
        default=10,
        metavar="N",
        help="flag clients with at least N login attempts (default: 10)",
    )
    parser.add_argument(
        "--min-failures",
        type=int,
        default=3,
        metavar="N",
        help="a success after N failures is a possible break-in (default: 3)",
    )


def _status_list(value: str) -> list[int]:
    """Parse ``401,403`` into ``[401, 403]``."""
    try:
        return [int(code) for code in value.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid status list '{value}'") from None


def _is_suspect(client: Client, min_attempts: int) -> bool:
    """Tell whether a client made many login attempts or got in after failing."""
    return client.attempts >= min_attempts or client.break_in
