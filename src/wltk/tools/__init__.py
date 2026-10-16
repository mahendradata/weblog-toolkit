"""Tool registry.

Each tool is a module in this package exposing:

* ``NAME`` - the subcommand name (``wltk <NAME>``)
* ``HELP`` - one-line description shown in ``wltk --help``
* ``add_arguments(parser)`` - declare the tool's CLI arguments
* ``run(args)`` - execute the tool and return an exit code

To add a tool, create a module and list it in a category of ``CATEGORIES``.
"""

from types import ModuleType

from . import (
    find_attacks,
    find_bruteforce,
    find_errors,
    find_scanners,
    first_last,
    fix_time,
    get_agent,
    get_hostname,
    get_method,
    get_status,
    get_time,
    get_url,
    hash,
    merge,
    pivot,
    rare,
    report,
    stats,
    timeline,
    to_csv,
    to_json,
    top,
    verify,
)

CATEGORIES: dict[str, list[ModuleType]] = {
    "Narrow the evidence": [
        get_hostname,
        get_time,
        get_url,
        get_status,
        get_agent,
        get_method,
    ],
    "Spot attacks": [find_attacks, find_scanners, find_bruteforce, find_errors],
    "Reconstruct what an actor did": [timeline, first_last, pivot],
    "Summarize": [top, rare, stats],
    "Check the log itself": [verify, hash, fix_time, merge],
    "Convert and report": [to_csv, to_json, report],
}

TOOLS: list[ModuleType] = [tool for tools in CATEGORIES.values() for tool in tools]
