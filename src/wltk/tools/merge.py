"""``wltk merge`` - combine several logs into one, ordered by time."""

import argparse
from datetime import UTC, datetime

from ..logio import (
    add_output_argument,
    parse_line,
    parse_time,
    read_lines,
    write_output,
)

NAME = "merge"
HELP = "Merge several logs into one, sorted by time"

EARLIEST = datetime.min.replace(tzinfo=UTC)


def run(args: argparse.Namespace) -> int:
    """Run the ``merge`` tool and return an exit code."""
    entries: list[tuple[datetime, str]] = []
    for path in args.logfiles:
        previous = EARLIEST
        for line in read_lines(path):
            fields = parse_line(line)
            time = parse_time(fields["time"] or "") if fields else None
            previous = time or previous  # unreadable lines stay by their neighbour
            entries.append((previous, line))
    entries.sort(key=lambda entry: entry[0])
    write_output(args.output, lambda out: out.writelines(line for _, line in entries))
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``merge`` tool."""
    parser.add_argument("logfiles", nargs="+", help="log files to merge ('-' = stdin)")
    add_output_argument(parser)
