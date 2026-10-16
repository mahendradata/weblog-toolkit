"""``wltk stats`` - traffic volume per minute, hour or day."""

import argparse

from ..logio import (
    INTERVALS,
    add_summary_arguments,
    bucket_rows,
    emit_rows,
    read_fields,
)

NAME = "stats"
HELP = "Requests, visitors, bytes and errors per time interval"


def run(args: argparse.Namespace) -> int:
    """Run the ``stats`` tool and return an exit code."""
    rows = bucket_rows(read_fields(args.logfile), args.interval)
    header = (args.interval, "requests", "visitors", "bytes", "errors")
    return emit_rows(args, header, rows)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``stats`` tool."""
    add_summary_arguments(parser)
    parser.add_argument(
        "-i",
        "--interval",
        choices=list(INTERVALS),
        default="hour",
        help="size of the time buckets (default: hour)",
    )
