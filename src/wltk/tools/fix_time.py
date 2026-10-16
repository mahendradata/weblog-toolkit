"""``wltk fix_time`` - rewrite log timestamps into one timezone."""

import argparse
import re
import sys
from datetime import timedelta, timezone

from ..logio import (
    COMBINED,
    TIME_FORMAT,
    add_logfile_argument,
    add_output_argument,
    parse_time,
    read_lines,
    write_output,
)

NAME = "fix_time"
HELP = "Rewrite timestamps into one timezone (default UTC)"

OFFSET = re.compile(r"(?:UTC|Z)|(?P<sign>[+-])(?P<hours>\d{2}):?(?P<minutes>\d{2})")


def run(args: argparse.Namespace) -> int:
    """Run the ``fix_time`` tool and return an exit code."""
    fixed = [_fix_line(line, args.tz) for line in read_lines(args.logfile)]
    write_output(args.output, lambda out: out.writelines(text for text, _ in fixed))
    unchanged = sum(not ok for _, ok in fixed)
    if unchanged:
        print(f"wltk: {unchanged} line(s) left unchanged", file=sys.stderr)
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``fix_time`` tool."""
    add_logfile_argument(parser)
    add_output_argument(parser)
    parser.add_argument(
        "--tz",
        type=_offset,
        default=timezone.utc,
        metavar="OFFSET",
        help="target timezone: +HHMM, UTC, or --tz=-HH:MM for negative (default: UTC)",
    )


def _offset(value: str) -> timezone:
    """Parse ``+0330``, ``-05:00``, ``Z`` or ``UTC`` into a timezone."""
    match = OFFSET.fullmatch(value)
    if match is None:
        raise argparse.ArgumentTypeError(f"invalid timezone '{value}'")
    if match["sign"] is None:
        return timezone.utc
    delta = timedelta(hours=int(match["hours"]), minutes=int(match["minutes"]))
    return timezone(-delta if match["sign"] == "-" else delta)


def _fix_line(line: str, zone: timezone) -> tuple[str, bool]:
    """Return the line with its timestamp converted, and whether that worked."""
    match = COMBINED.match(line)
    time = parse_time(match["time"]) if match else None
    if match is None or time is None:
        return line, False
    start, end = match.span("time")
    converted = time.astimezone(zone).strftime(TIME_FORMAT)
    return line[:start] + converted + line[end:], True
