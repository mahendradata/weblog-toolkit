"""Shared helpers for reading, parsing, filtering and summarizing log files."""

import argparse
import csv
import re
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from itertools import islice
from typing import Any, TextIO

TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
INTERVALS = {"minute": "%Y-%m-%d %H:%M", "hour": "%Y-%m-%d %H:00", "day": "%Y-%m-%d"}

# 127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /a.gif HTTP/1.0" 200 2326
COMMON = re.compile(
    r"(?P<hostname>\S+) "  # Client IP or hostname
    r"(?P<identity>\S*) "  # identd, usually "-"
    r"(?P<userid>\S*) "  # Authenticated user id
    r"\[(?P<time>[^\]]+)\] "  # Timestamp
    r'"(?P<method>\S+) '  # HTTP method
    r"(?P<url>\S+) "  # Requested URL
    r'(?P<protocol>[^"]+)" '  # Protocol/version
    r"(?P<status>\d{3}) "  # Status code
    r"(?P<size>\S+)"  # Response size ("-" if zero)
)

# Common + "http://example.com/start.html" "Mozilla/4.08" ["optional extra"]
COMBINED = re.compile(
    COMMON.pattern
    + r' "(?P<referer>[^"]*)"'  # Referer header (may be "-")
    + r' "(?P<user_agent>[^"]*)"'  # User-Agent string
    + r'(?: "(?P<extra>[^"]*)")?'  # Optional extra field, e.g. X-Forwarded-For
)

FORMATS: dict[str, re.Pattern[str]] = {"combined": COMBINED, "common": COMMON}

Fields = dict[str, str | None]
Keep = Callable[[Fields], bool]
Row = tuple[str | int | float | None, ...]
Record = dict[str, Any]


# --- reading and parsing --------------------------------------------------


def read_lines(path: str) -> Iterator[str]:
    """Yield the lines of a log file; ``"-"`` reads from stdin.

    Invalid UTF-8 bytes are replaced instead of raising.
    """
    if path == "-":
        yield from sys.stdin
        return
    with open(path, encoding="utf-8", errors="replace") as file:
        yield from file


def parse_time(value: str) -> datetime | None:
    """Parse a log timestamp, returning ``None`` if it is not in log format."""
    try:
        return datetime.strptime(value, TIME_FORMAT)
    except ValueError:
        return None


def parse_line(line: str) -> Fields | None:
    """Split a Combined or Common log line into fields; ``None`` if malformed."""
    match = COMBINED.match(line) or COMMON.match(line)
    return match.groupdict() if match else None


def read_fields(path: str) -> Iterator[Fields]:
    """Yield the parsed fields of every well-formed line of a log file."""
    return (fields for line in read_lines(path) if (fields := parse_line(line)))


def read_timed(path: str) -> Iterator[tuple[datetime, Fields]]:
    """Yield ``(time, fields)`` for lines whose timestamp can be read."""
    for fields in read_fields(path):
        if time := parse_time(fields["time"] or ""):
            yield time, fields


def size_of(fields: Fields) -> int:
    """Return the response size in bytes (``-`` or invalid counts as 0)."""
    size = fields["size"] or ""
    return int(size) if size.isdigit() else 0


def is_error(fields: Fields) -> bool:
    """Tell whether the response status is 4xx or 5xx."""
    return int(fields["status"] or 0) >= 400


def parse_log(path: str, pattern: re.Pattern[str] = COMBINED) -> Iterator[Record]:
    """Yield one typed record per log line matching ``pattern``.

    Other lines are skipped. ``status`` and ``size`` are ints and ``time`` is a
    datetime (``None`` if unreadable).

    Args:
        path: Log file path, or ``"-"`` to read from stdin.
        pattern: Regex with named groups, one per field.
    """
    for line in read_lines(path):
        if match := pattern.match(line):
            fields = match.groupdict()
            yield fields | {
                "status": int(fields["status"]),
                "size": size_of(fields),
                "time": parse_time(fields["time"]),
            }


# --- command-line arguments -----------------------------------------------


def add_logfile_argument(parser: argparse.ArgumentParser) -> None:
    """Add the ``logfile`` argument (a path, or ``-`` for stdin)."""
    parser.add_argument("logfile", help="path to the access log, or '-' for stdin")


def add_output_argument(
    parser: argparse.ArgumentParser, what: str = "the lines"
) -> None:
    """Add ``-o/--output``; ``what`` names the result in the help text."""
    parser.add_argument(
        "-o", "--output", metavar="FILE", help=f"write {what} to FILE, not stdout"
    )


def add_limit_argument(
    parser: argparse.ArgumentParser, what: str = "rows", default: int | None = None
) -> None:
    """Add ``-n/--limit``; without a ``default`` all ``what`` are output."""
    help_text = f"only the first N {what}"
    if default is not None:
        help_text = f"number of {what} (default: {default})"
    parser.add_argument(
        "-n", "--limit", type=int, default=default, metavar="N", help=help_text
    )


def add_filter_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the arguments shared by filter tools."""
    add_logfile_argument(parser)
    add_output_argument(parser)


def add_summary_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the arguments shared by tools that print a table."""
    add_logfile_argument(parser)
    add_output_argument(parser, "the result as CSV")
    parser.add_argument(
        "--csv", action="store_true", help="print CSV instead of an aligned table"
    )


def add_convert_arguments(parser: argparse.ArgumentParser, target: str) -> None:
    """Add the arguments shared by tools converting a log to ``target``."""
    add_logfile_argument(parser)
    parser.add_argument(
        "-f",
        "--format",
        choices=sorted(FORMATS),
        default="combined",
        help="log format (default: combined)",
    )
    add_output_argument(parser, target)
    add_limit_argument(parser)


# --- output ---------------------------------------------------------------


def write_output(path: str | None, write: Callable[[TextIO], None]) -> None:
    """Call ``write`` with stdout, or with the file ``path`` when one is given."""
    if path is None:
        write(sys.stdout)
        return
    with open(path, "w", encoding="utf-8", newline="") as file:
        write(file)


def write_csv(out: TextIO, header: Row, rows: Iterable[Row]) -> None:
    """Write a header and rows as CSV."""
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)


def record_text(value: Any) -> str:
    """Render a record value as text (ISO format for datetimes, empty for None)."""
    if value is None:
        return ""
    return value.isoformat() if isinstance(value, datetime) else str(value)


def load_records(args: argparse.Namespace) -> list[Record]:
    """Parse the log named by ``args`` (honouring ``--format`` and ``--limit``).

    Prints an error when no line matched; the returned list is then empty.
    """
    records = list(islice(parse_log(args.logfile, FORMATS[args.format]), args.limit))
    if not records:
        print(f"wltk: no lines matched the '{args.format}' format", file=sys.stderr)
    return records


def run_filter(args: argparse.Namespace, keep: Keep) -> int:
    """Output, unchanged, the log lines whose parsed fields satisfy ``keep``.

    Lines that cannot be parsed are dropped. Nothing is written (and exit code 1
    is returned) when no line matches.
    """
    lines = [
        line
        for line in read_lines(args.logfile)
        if (fields := parse_line(line)) and keep(fields)
    ]
    if not lines:
        print("wltk: no matching lines", file=sys.stderr)
        return 1
    write_output(args.output, lambda out: out.writelines(lines))
    return 0


def emit_rows(
    args: argparse.Namespace,
    header: Row,
    rows: Sequence[Row],
    empty: str = "no lines could be parsed",
) -> int:
    """Output a summary: CSV to ``--output`` or with ``--csv``, else a table.

    When there are no rows, ``empty`` is printed to stderr instead and 1 is returned.
    """
    if not rows:
        print(f"wltk: {empty}", file=sys.stderr)
        return 1
    if args.output is not None or args.csv:
        write_output(args.output, lambda out: write_csv(out, header, rows))
    else:
        _print_table(header, rows)
    return 0


def _print_table(header: Row, rows: Sequence[Row]) -> None:
    """Print a header and rows as an aligned table (numbers right-aligned)."""
    cells = [["" if c is None else str(c) for c in row] for row in (header, *rows)]
    widths = [max(map(len, column)) for column in zip(*cells)]
    for row, source in zip(cells, (header, *rows)):
        padded = [
            text.rjust(width) if isinstance(raw, int | float) else text.ljust(width)
            for text, raw, width in zip(row, source, widths)
        ]
        print("  ".join(padded).rstrip())


# --- counting -------------------------------------------------------------


def tally(rows: Iterable[Fields], by: str, weight: str = "count") -> Counter[str]:
    """Total ``weight`` (``count`` or ``bytes``) per distinct value of field ``by``."""
    totals: Counter[str] = Counter()
    for fields in rows:
        totals[fields.get(by) or "-"] += size_of(fields) if weight == "bytes" else 1
    return totals


def ranked_rows(totals: Counter[str], limit: int, rarest: bool = False) -> list[Row]:
    """Return ``(total, percent, value)`` rows for the top (or rarest) ``limit``."""
    grand_total = sum(totals.values())
    sign = 1 if rarest else -1
    ranking = sorted(totals.items(), key=lambda item: (sign * item[1], item[0]))
    return [
        (total, round(100 * total / grand_total, 1), value)
        for value, total in ranking[:limit]
    ]


@dataclass
class Bucket:
    """Running totals of one time interval."""

    requests: int = 0
    visitors: set[str] = field(default_factory=set)
    bytes: int = 0
    errors: int = 0


def bucket_rows(rows: Iterable[Fields], interval: str) -> list[Row]:
    """Return ``(period, requests, visitors, bytes, errors)`` per time interval.

    ``interval`` is a key of ``INTERVALS``. Lines with an unreadable timestamp are
    skipped; ``errors`` counts 4xx and 5xx responses.
    """
    buckets: dict[str, Bucket] = {}
    for fields in rows:
        time = parse_time(fields["time"] or "")
        if time is None:
            continue
        bucket = buckets.setdefault(time.strftime(INTERVALS[interval]), Bucket())
        bucket.requests += 1
        bucket.visitors.add(fields["hostname"] or "-")
        bucket.bytes += size_of(fields)
        bucket.errors += is_error(fields)
    return [
        (period, b.requests, len(b.visitors), b.bytes, b.errors)
        for period, b in sorted(buckets.items())
    ]
