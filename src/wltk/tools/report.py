"""``wltk report`` - one-page summary of an access log, as Markdown or HTML."""

import argparse
import html
import sys
from collections import Counter
from datetime import datetime, timedelta

from ..logio import (
    Fields,
    Row,
    add_limit_argument,
    add_logfile_argument,
    add_output_argument,
    bucket_rows,
    is_error,
    parse_time,
    ranked_rows,
    read_fields,
    size_of,
    tally,
    write_output,
)
from ..signatures import classify

NAME = "report"
HELP = "One-page summary of a log (Markdown or HTML)"

Section = tuple[str, Row, list[Row]]

TRAFFIC_COLUMNS = ("requests", "visitors", "bytes", "errors")

MAX_CELL = 100
CSS = (
    "body{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;"
    "padding:0 1rem}table{border-collapse:collapse;margin:0 0 1.5rem}"
    "th,td{border:1px solid #bbb;padding:.2rem .6rem;vertical-align:top}"
    "th{background:#eee;color:#111}td.num{text-align:right}"
    "td{word-break:break-all}"
)


def run(args: argparse.Namespace) -> int:
    """Run the ``report`` tool and return an exit code."""
    rows = list(read_fields(args.logfile))
    if not rows:
        print("wltk: no lines could be parsed", file=sys.stderr)
        return 1
    source = "stdin" if args.logfile == "-" else args.logfile
    sections = build_sections(rows, source, args.limit)
    render = render_html if _is_html(args) else render_markdown
    write_output(args.output, lambda out: out.write(render(args.title, sections)))
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``report`` tool."""
    add_logfile_argument(parser)
    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "html"],
        help="report format (default: html for *.html files, else markdown)",
    )
    add_output_argument(parser, "the report")
    add_limit_argument(parser, "rows per ranking", default=10)
    parser.add_argument("--title", default="Web server log report", help="report title")


def build_sections(rows: list[Fields], source: str, limit: int) -> list[Section]:
    """Compute the report sections (overview, traffic, rankings) from log lines."""
    times = [t for fields in rows if (t := parse_time(fields["time"] or ""))]
    interval = "hour"
    if times and max(times) - min(times) >= timedelta(days=2):
        interval = "day"
    errors = [fields for fields in rows if is_error(fields)]
    traffic = bucket_rows(rows, interval)
    categories = [classify(fields) for fields in rows]
    flagged = [f for f, found in zip(rows, categories) if found]
    by_category = Counter(category for found in categories for category in found)

    def ranking(
        title: str, by: str, source_rows: list[Fields], weight: str = "count"
    ) -> Section:
        totals = tally(source_rows, by, weight)
        unit = "requests" if weight == "count" else weight
        return (title, (unit, "percent", by), ranked_rows(totals, limit))

    return [
        ("Overview", ("Metric", "Value"), _overview(rows, times, errors, source)),
        (f"Traffic per {interval}", (interval, *TRAFFIC_COLUMNS), traffic),
        ranking("Top clients by requests", "hostname", rows),
        ranking("Top clients by bytes", "hostname", rows, "bytes"),
        ranking("Clients with most errors (4xx/5xx)", "hostname", errors),
        ranking("Top URLs", "url", rows),
        ranking("Status codes", "status", rows),
        ranking("Top User-Agents", "user_agent", rows),
        (
            "Flagged requests by attack category",
            ("hits", "percent", "category"),
            ranked_rows(by_category, limit),
        ),
        ranking("Clients with most flagged requests", "hostname", flagged),
        (
            "Rarest URLs",
            ("requests", "percent", "url"),
            ranked_rows(tally(rows, "url"), limit, rarest=True),
        ),
    ]


def render_markdown(title: str, sections: list[Section]) -> str:
    """Render the sections as a Markdown document."""
    parts = [f"# {title}\n"]
    for name, header, rows in sections:
        parts.append(f"\n## {name}\n")
        if not rows:
            parts.append("\nNo data.\n")
            continue
        align = ["---:" if _is_number(cell) else "---" for cell in rows[0]]
        lines = [header, align, *rows]
        parts.append("\n" + "\n".join(_md_row(line) for line in lines) + "\n")
    return "".join(parts)


def render_html(title: str, sections: list[Section]) -> str:
    """Render the sections as a self-contained HTML page."""
    body = [f"<h1>{html.escape(title)}</h1>"]
    for name, header, rows in sections:
        body.append(f"<h2>{html.escape(name)}</h2>")
        if not rows:
            body.append("<p>No data.</p>")
            continue
        head = "".join(f"<th>{html.escape(str(cell))}</th>" for cell in header)
        body.append(f"<table><tr>{head}</tr>")
        body.extend(f"<tr>{_html_cells(row)}</tr>" for row in rows)
        body.append("</table>")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body>{''.join(body)}</body></html>\n"
    )


def _overview(
    rows: list[Fields],
    times: list[datetime],
    errors: list[Fields],
    source: str,
) -> list[Row]:
    """Headline numbers: period, volume, visitors, error rate and peak hour."""
    peak = max(bucket_rows(rows, "hour"), key=lambda row: row[1], default=None)
    period = "unknown"
    if times:
        period = f"{min(times):%Y-%m-%d %H:%M} to {max(times):%Y-%m-%d %H:%M}"
    return [
        ("Source", source),
        ("Period", period),
        ("Requests", len(rows)),
        ("Unique clients", len({fields["hostname"] for fields in rows})),
        ("Bytes sent", sum(size_of(fields) for fields in rows)),
        ("Error rate (4xx/5xx)", f"{100 * len(errors) / len(rows):.1f}%"),
        ("Busiest hour", f"{peak[0]} ({peak[1]} requests)" if peak else "unknown"),
    ]


def _is_html(args: argparse.Namespace) -> bool:
    """Tell whether the report should be HTML (``--format`` or file extension)."""
    if args.format is not None:
        return args.format == "html"
    return bool(args.output) and args.output.lower().endswith((".html", ".htm"))


def _is_number(cell: object) -> bool:
    """Tell whether a table cell is numeric (for right alignment)."""
    return isinstance(cell, int | float)


def _clip(cell: object) -> str:
    """Render a cell as text, shortening very long values."""
    text = str(cell)
    return text if len(text) <= MAX_CELL else text[: MAX_CELL - 1] + "…"


def _md_row(row: Row) -> str:
    """Format one Markdown table row, escaping pipes and line breaks."""
    cells = (
        html.escape(_clip(cell), quote=False).replace("|", "\\|").replace("\n", " ")
        for cell in row
    )
    return "| " + " | ".join(cells) + " |"


def _html_cells(row: Row) -> str:
    """Format the cells of one HTML table row (numbers right-aligned)."""
    return "".join(
        f'<td class="num">{cell}</td>'
        if _is_number(cell)
        else f"<td>{html.escape(_clip(cell))}</td>"
        for cell in row
    )
