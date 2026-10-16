"""``wltk to_json`` - convert an access log to JSON (printed or saved to a file)."""

import argparse
import json
from typing import TextIO

from ..logio import (
    Record,
    add_convert_arguments,
    load_records,
    record_text,
    write_output,
)

NAME = "to_json"
HELP = "Convert a log to JSON Lines or a JSON array"


def run(args: argparse.Namespace) -> int:
    """Run the ``to_json`` tool and return an exit code."""
    records = load_records(args)
    if not records:
        return 1
    write_output(args.output, lambda out: _write_json(records, out, args.array))
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``to_json`` tool."""
    add_convert_arguments(parser, "JSON")
    parser.add_argument(
        "--array",
        action="store_true",
        help="output one JSON array instead of one object per line",
    )


def _write_json(records: list[Record], out: TextIO, array: bool) -> None:
    """Write records as JSON Lines, or as a single JSON array."""
    if array:
        out.write(json.dumps(records, default=record_text, indent=2) + "\n")
        return
    for record in records:
        out.write(json.dumps(record, default=record_text) + "\n")
