"""Single entry point for all wltk tools: ``wltk <tool> [options]``."""

import argparse
import io
import sys
from collections.abc import Sequence

from . import __version__
from .tools import CATEGORIES, TOOLS


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with one subcommand per registered tool."""
    parser = argparse.ArgumentParser(
        prog="wltk",
        description="Web server log analysis toolkit.",
        epilog=_tool_listing(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"wltk {__version__}")
    sub = parser.add_subparsers(dest="tool", metavar="<tool>", required=True)
    for tool in TOOLS:
        # No help= here: the tools are listed by category in the epilog instead.
        tool_parser = sub.add_parser(tool.NAME, description=tool.HELP)
        tool.add_arguments(tool_parser)
        tool_parser.set_defaults(run=tool.run)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to the selected tool and return its exit code."""
    args = build_parser().parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")  # logs may hold non-ASCII text
    try:
        return args.run(args)
    except OSError as exc:
        print(f"wltk: {exc}", file=sys.stderr)
        return 1


def _tool_listing() -> str:
    """Format the tools, grouped by category, for the ``--help`` footer."""
    width = max(len(tool.NAME) for tool in TOOLS)
    lines = ["tools:"]
    for category, tools in CATEGORIES.items():
        lines.append(f"\n  {category}")
        lines.extend(f"    {tool.NAME:<{width}}  {tool.HELP}" for tool in tools)
    lines.append("\nRun 'wltk <tool> --help' for the options of a tool.")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
