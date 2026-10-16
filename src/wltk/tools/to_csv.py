"""``wltk to_csv`` - convert an access log to CSV (printed or saved to a file)."""

import argparse

from ..logio import (
    add_convert_arguments,
    load_records,
    record_text,
    write_csv,
    write_output,
)

NAME = "to_csv"
HELP = "Convert a log to CSV"


def run(args: argparse.Namespace) -> int:
    """Run the ``to_csv`` tool and return an exit code."""
    records = load_records(args)
    if not records:
        return 1
    header = tuple(records[0])
    rows = [tuple(record_text(value) for value in r.values()) for r in records]
    write_output(args.output, lambda out: write_csv(out, header, rows))
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``to_csv`` tool."""
    add_convert_arguments(parser, "CSV")
