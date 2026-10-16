"""``wltk verify`` - check a log for gaps, disorder, malformed lines and truncation."""

import argparse
import sys
from datetime import datetime, timedelta

from ..logio import (
    Row,
    add_limit_argument,
    add_summary_arguments,
    emit_rows,
    parse_line,
    parse_time,
    read_lines,
)

NAME = "verify"
HELP = "Check a log for gaps, disorder, malformed lines, truncation"

EXIT_PROBLEMS = 3


def run(args: argparse.Namespace) -> int:
    """Run the ``verify`` tool; exit code 3 means problems were found."""
    problems: list[Row] = []
    latest: datetime | None = None
    last_zone: timedelta | None = None
    count = 0
    last_line = ""
    for count, line in enumerate(read_lines(args.logfile), start=1):
        last_line = line
        if not line.strip():
            continue
        fields = parse_line(line)
        if fields is None:
            problems.append(("malformed", count, line.strip()[:80]))
            continue
        time = parse_time(fields["time"] or "")
        if time is None:
            problems.append(("bad-timestamp", count, fields["time"]))
            continue
        problems += _time_problems(count, time, latest, last_zone, args)
        latest = max(latest or time, time)
        last_zone = time.utcoffset()
    if count and not last_line.endswith("\n"):
        problems.append(("truncated", count, "last line has no line break"))

    if not problems:
        print(f"OK: {count} lines checked, no problems found")
        return 0
    emit_rows(args, ("check", "line", "detail"), problems[: args.limit])
    print(f"wltk: {count} lines checked, {len(problems)} problems", file=sys.stderr)
    return EXIT_PROBLEMS


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``verify`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "--gap",
        type=float,
        default=60,
        metavar="MINUTES",
        help="report silences longer than this (default: 60)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=5,
        metavar="SECONDS",
        help="ignore lines up to this far out of order (default: 5)",
    )
    add_limit_argument(parser, "problems", default=100)


def _time_problems(
    number: int,
    time: datetime,
    latest: datetime | None,
    last_zone: timedelta | None,
    args: argparse.Namespace,
) -> list[Row]:
    """Check one timestamp against the latest one seen so far."""
    problems: list[Row] = []
    if latest is not None:
        delta = time - latest
        if delta < -timedelta(seconds=args.tolerance):
            problems.append(("out-of-order", number, f"{-delta} before a later entry"))
        elif delta > timedelta(minutes=args.gap):
            problems.append(("gap", number, f"{delta} without entries before {time}"))
    if last_zone is not None and time.utcoffset() != last_zone:
        problems.append(("timezone-change", number, f"now {time:%z}"))
    return problems
