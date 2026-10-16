# weblog-toolkit

A BusyBox-style toolkit for analyzing web server logs, built with digital
forensic investigations in mind. Every tool is available through a single
command, `wltk`:

```
wltk <tool> [options]
```

It reads Apache and Nginx access logs in the Combined or Common Log Format, has
no third-party dependencies, and never modifies its input: results go to the
terminal or to a file you name with `-o`.

| Category | Tool | What it does |
| --- | --- | --- |
| **Narrow the evidence** | `get_hostname` | Keep the lines of given source IPs, CIDR ranges or hostnames |
|  | `get_time` | Keep the lines inside a time window |
|  | `get_url` | Keep the lines whose URL matches a regex |
|  | `get_status` | Keep the lines with given HTTP status codes or classes |
|  | `get_agent` | Keep the lines whose User-Agent matches a regex |
|  | `get_method` | Keep the lines with given HTTP methods |
| **Spot attacks** | `find_attacks` | Flag requests matching attack signatures (SQLi, XSS, traversal, ...) |
|  | `find_scanners` | Find clients with many 404s or a known scanner User-Agent |
|  | `find_bruteforce` | Find clients hammering login URLs, or logging in after failures |
|  | `find_errors` | Find time intervals with bursts of server errors |
| **Reconstruct what an actor did** | `timeline` | Chronological requests of given clients, in sessions |
|  | `first_last` | When each client was first and last seen |
|  | `pivot` | Find clients that requested the same URLs as a suspect |
| **Summarize** | `top` | Most frequent values of a field, by requests or bytes |
|  | `rare` | Least frequent values of a field |
|  | `stats` | Requests, visitors, bytes and errors per time interval |
| **Check the log itself** | `verify` | Check a log for gaps, disorder, malformed lines, truncation |
|  | `hash` | Write a hash manifest of log files, or verify files against one |
|  | `fix_time` | Rewrite timestamps into one timezone (default UTC) |
|  | `merge` | Merge several logs into one, sorted by time |
| **Convert and report** | `to_csv` | Convert a log to CSV |
|  | `to_json` | Convert a log to JSON Lines or a JSON array |
|  | `report` | One-page summary of a log (Markdown or HTML) |

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mahendradata/weblog-toolkit.git
cd weblog-toolkit
uv sync                 # create the environment and install wltk + dev tools
uv run wltk --help
```

To install `wltk` as a standalone command available everywhere:

```bash
uv tool install .
wltk --help
```

## Usage

```bash
wltk --help             # list all tools, by category
wltk to_csv --help      # options of a single tool
wltk --version
```

Conventions shared by all tools:

- `logfile` is a path, or `-` to read from stdin, so tools chain with pipes
  (`hash` takes files only).
- `-o FILE` writes the result to a file instead of the terminal.
- Lines that are not in the Combined or Common format are skipped (use
  `verify` to find them).
- Exit code `0` means success, `1` that the file cannot be read or nothing
  matched (or, for `hash --check`, that a file differs), `2` a usage error.
  `verify` returns `3` when it finds problems.
- Options like `-i` and `-s` can be repeated; a line is kept if it matches
  **any** of the values. Chain tools to require **all** conditions.

### An investigation, step by step

```bash
# 0. Preserve the evidence and make sure the log is intact
wltk hash access.log -o access.log.sha256
wltk verify access.log

# 1. Get the big picture
wltk report access.log -o report.html
wltk top access.log -n 5

# 2. Look for attacks
wltk find_attacks access.log
wltk find_bruteforce access.log
wltk find_scanners access.log

# 3. Follow a suspect
wltk first_last access.log -i 6.6.6.6
wltk timeline access.log -i 6.6.6.6
wltk pivot access.log -i 6.6.6.6

# 4. Extract their traffic as evidence, and report on it
wltk get_hostname access.log -i 6.6.6.6 -o suspect.log
wltk report suspect.log --title "Suspect 6.6.6.6" -o suspect.html

# Later: prove the original log has not changed
wltk hash --check access.log.sha256
```

## Narrow the evidence

`get_hostname`, `get_time`, `get_url`, `get_status`, `get_agent` and
`get_method` keep only the lines you care about. Matching lines are output
**unchanged** (same format as the original log), so the tools can be chained
with each other and with every other tool.

| Argument              | Description                                 |
| --------------------- | ------------------------------------------- |
| `logfile`             | Log file path, or `-` to read from stdin    |
| `-o`, `--output FILE` | Write the lines to FILE instead of printing |

| Tool           | Option                | Matches                                                       |
| -------------- | --------------------- | ------------------------------------------------------------- |
| `get_hostname` | `-i`, `--ip IP`       | Source IP, CIDR range (`10.0.0.0/24`) or hostname; repeatable |
| `get_time`     | `--from`, `--to TIME` | Time window, ISO 8601, inclusive (at least one is required)   |
| `get_url`      | `-u`, `--url REGEX`   | Regex searched in the URL, as logged and percent-decoded      |
| `get_status`   | `-s`, `--status CODE` | Status code (`404`) or class (`4xx`); repeatable              |
| `get_agent`    | `-a`, `--agent REGEX` | Case-insensitive regex in the User-Agent (combined format)    |
| `get_method`   | `-m`, `--method NAME` | HTTP method, case-insensitive; repeatable                     |

Times without a timezone (`2019-01-22T03:56:00`) are read in the timezone of
each log line; add an offset or `Z` to be explicit. A date alone means midnight.

```bash
wltk get_hostname access.log -i 31.56.96.0/24 -o subnet.log
wltk get_time access.log --from 2019-01-22T03:56:00 --to 2019-01-22T04:06:00
wltk get_method access.log -m POST | wltk get_status - -s 401 -s 403
wltk get_url access.log -u '\.\./'              # also finds %2e%2e%2f
wltk get_agent access.log -a 'sqlmap|nikto|nmap'

# Chain: one client's successful requests inside a window, as CSV
wltk get_hostname access.log -i 40.77.167.129 \
  | wltk get_time - --from 2019-01-22T03:56:00 \
  | wltk get_status - -s 2xx \
  | wltk to_csv - -o client.csv
```

`get_time` exits with `2` if given no bound.

## Spot attacks

`find_attacks`, `find_scanners`, `find_bruteforce` and `find_errors` print a
table (see [Summary tables](#summary-tables) for `--csv` and `-o`).

### `find_attacks`

Matches every request against signatures for: `sql-injection`, `xss`,
`path-traversal`, `command-injection`, `web-shell`, `log4shell`,
`sensitive-file` (`.env`, `.git/`, `wp-config`, `phpmyadmin`...) and
`scanner-agent` (sqlmap, Nikto, Nmap, ...). URLs are percent-decoded twice, so
`%252e%252e%252f` is still caught. One row per request and category.

| Option               | Description                                                 |
| -------------------- | ----------------------------------------------------------- |
| `-c`, `--category C` | Only this category (repeatable; default: all)               |
| `--raw`              | Output the flagged log lines unchanged, to chain other tools |

```bash
wltk find_attacks access.log                  # time, hostname, category, status, url
wltk find_attacks access.log -c log4shell -c sql-injection
wltk find_attacks access.log --raw | wltk top - -b hostname   # who attacks most
```

Signatures are heuristics: a hit is a lead to check (look at the `status`), not
proof of compromise, and a clean result does not prove the site was not attacked.

### `find_scanners`

Lists clients with many `404` responses (probing for pages) or a scanner
User-Agent: `hostname`, `requests`, `distinct_urls`, `not_found`,
`scanner_agent`. Use `--min-404 N` to set the threshold (default 20).

### `find_bruteforce`

Looks at `POST` requests to login-like URLs and lists clients with many
attempts, or with a successful login **after** repeated failures (a possible
break-in): `hostname`, `attempts`, `failures`, `successes`,
`success_after_failures`.

| Option             | Description                                                         |
| ------------------ | ------------------------------------------------------------------- |
| `-u`, `--url REGEX` | Case-insensitive regex for login URLs (default: `login\|signin\|sign-in\|auth\|admin\|xmlrpc\|account`) |
| `--fail-status CODES` | Comma-separated status codes meaning a failed login (default: `401,403`) |
| `--min-attempts N` | Flag clients with at least N attempts (default: 10)                 |
| `--min-failures N` | A success after N failures is flagged (default: 3)                  |

Applications that answer a failed login with `200` and a success with `302`
(WordPress) need `--fail-status 200`. The log is read in file order, so merge
and sort logs first (`merge`).

### `find_errors`

Finds time intervals with bursts of errors, which often mean an exploit hit a
bug: `minute`, `errors`, `clients`, `top_url`. Options: `-s` (status code or
class, default `5xx`), `-i minute|hour|day` (default `minute`), `--min N`
(default 10).

## Reconstruct what an actor did

### `timeline`

Chronological list of everything the given clients requested, split into
sessions: `hostname`, `session`, `time`, `method`, `url`, `status`, `bytes`.
Options: `-i IP` (required, repeatable, CIDR allowed) and `--gap MINUTES` (idle
time that starts a new session, default 30). Lines are sorted by time even if the
log is not.

### `first_last`

When each client was first and last seen: `hostname`, `first_seen`, `last_seen`,
`minutes`, `requests`, ordered by first appearance. Options: `-i IP` to restrict
to some clients, `-n N` for the first N.

### `pivot`

Starting from a suspect, finds other clients that requested the same URLs, which
links attackers who rotate addresses: `hostname`, `shared_urls`, `examples`.
URLs requested by many clients (like `/`) would link everybody, so URLs seen
from more than `--max-hosts N` clients (default 20) are ignored. Other options:
`-i IP` (required), `--min-shared N` (default 1), `-n N` (default 20).

```bash
wltk timeline access.log -i 6.6.6.6 --gap 10
wltk first_last access.log -i 6.6.6.0/24
wltk pivot access.log -i 6.6.6.6 --min-shared 2
```

## Summarize

`top`, `rare` and `stats` answer "what is in this log?".

| Tool    | Options                               | Result                                               |
| ------- | ------------------------------------- | ---------------------------------------------------- |
| `top`   | `-b FIELD`, `-w count\|bytes`, `-n N` | Most frequent values of a field (default `hostname`) |
| `rare`  | `-b FIELD`, `-n N`                    | Least frequent values (default `url`)                |
| `stats` | `-i minute\|hour\|day`                | Requests, unique visitors, bytes and errors (status >= 400) per interval |

`FIELD` is one of `hostname`, `url`, `user_agent`, `referer`, `status`, `method`
or `userid`. `top -w bytes` ranks by bytes sent, which highlights sources that
downloaded unusually large amounts of data.

```bash
wltk top access.log -w bytes -n 5               # who pulled the most data
wltk top access.log -b url -n 20
wltk rare access.log -b user_agent -n 5         # normal traffic repeats, odd traffic does not
wltk stats access.log -i day -o daily.csv
```

```
count  percent  hostname
   88      8.8  66.249.66.194
   83      8.3  66.249.66.91
   78      7.8  130.185.74.243
```

### Summary tables

Tools that print tables (`find_*`, `timeline`, `first_last`, `pivot`, `top`,
`rare`, `stats`, `verify`) share these arguments:

| Argument              | Description                                               |
| --------------------- | --------------------------------------------------------- |
| `logfile`             | Log file path, or `-` to read from stdin                  |
| `--csv`               | Print CSV instead of an aligned table                     |
| `-o`, `--output FILE` | Write the result to FILE (always CSV) instead of printing |

They exit with `1` and print nothing to stdout when there is nothing to show
(`verify` prints `OK` instead and exits with `0`).

## Check the log itself

### `verify`

Checks that a log looks complete and untampered: malformed lines, unreadable
timestamps, **out-of-order** entries, **gaps** with no entries, **timezone
changes** and a **truncated** last line. Prints one row per problem
(`check`, `line`, `detail`) and exits with `3` if there are any.

| Option                | Description                                              |
| --------------------- | -------------------------------------------------------- |
| `--gap MINUTES`       | Report silences longer than this (default: 60)           |
| `--tolerance SECONDS` | Ignore lines up to this far out of order (default: 5; servers log a request when it finishes) |
| `-n`, `--limit N`     | Number of problems to list (default: 100)                |
| `--csv`, `-o FILE`    | As for the other tables, see [Summary tables](#summary-tables) |

```
$ wltk verify access.log
check           line  detail
out-of-order       2  1:00:00 before a later entry
gap                5  4:00:00 without entries before 2025-07-10 14:00:00+03:30
```

A gap or an edit does not prove tampering (a quiet site has gaps), but they are
where to look first.

### `hash`

Creates a manifest of `digest  filename` lines (the `sha256sum` format) with a
header recording when it was made and each file's size and modification time,
and verifies files against a manifest later.

```bash
wltk hash access.log error.log -o evidence.sha256     # create
wltk hash --check evidence.sha256                     # prints OK / FAILED per file
sha256sum -c evidence.sha256                          # standard tools work too
```

`-a sha256|sha512|sha1|md5` selects the algorithm (default `sha256`; use the
same one with `--check`). `--check` exits with `1` if any file differs or is missing.

### `fix_time`

Rewrites every timestamp into one timezone and leaves the rest of the line
untouched. Useful before comparing logs from several servers. `--tz` accepts
`+0330`, `UTC` (default) or, for negative offsets, `--tz=-05:00`. Lines whose
timestamp cannot be read are copied unchanged and counted on stderr.

### `merge`

Merges several logs into one, sorted by time. Timezones are taken into account,
and unreadable lines stay next to the line before them.

```bash
wltk fix_time web1.log --tz +0000 -o web1.utc.log
wltk merge web1.log web2.log -o all.log
```

`merge` loads all lines in memory.

## Convert and report

### `to_csv` and `to_json`

Convert a log to typed records: `status` and `size` are numbers and `time` is
an ISO 8601 timestamp. `to_json` writes JSON Lines (one object per request) or,
with `--array`, one JSON array.

| Option                | Description                          |
| --------------------- | ------------------------------------ |
| `logfile`             | Log file path, or `-` for stdin      |
| `-f`, `--format`      | `combined` (default) or `common`     |
| `-o`, `--output FILE` | Write to FILE instead of printing    |
| `-n`, `--limit N`     | Only output the first N rows         |
| `--array`             | (`to_json`) one JSON array           |

Columns: `hostname`, `identity`, `userid`, `time`, `method`, `url`, `protocol`,
`status`, `size` (plus `referer`, `user_agent`, `extra` for the combined format).

```bash
wltk to_csv access.log -o access.csv
zcat access.log.gz | wltk to_csv - -f common -o access.csv
wltk to_json access.log --array -o access.json
```

### `report`

A one-page summary of a log, ready to attach to a case file: an overview
(period, requests, unique clients, bytes, error rate, busiest hour), traffic per
hour (or per day when the log spans two days or more), and rankings of the top
clients by requests and by bytes, the clients with the most errors, top URLs,
status codes, top User-Agents, **flagged requests by attack category**, the
clients with the most flagged requests, and the rarest URLs.

| Option                | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| `-f`, `--format`      | `markdown` or `html` (default: html for `*.html`, else markdown) |
| `-o`, `--output FILE` | Write the report to FILE instead of printing                      |
| `-n`, `--limit N`     | Rows per ranking (default: 10)                                    |
| `--title TEXT`        | Report title                                                      |

The HTML report is a single self-contained file. Values taken from the log
(URLs, User-Agents) are escaped in both formats, so attacker-supplied payloads
such as `<script>` are shown as text and never executed.

```bash
wltk report access.log -o report.md
wltk get_hostname access.log -i 66.249.66.194 \
  | wltk report - --title "Client 66.249.66.194" -o client.html
```

## Use as a Python library

```python
from collections import Counter

from wltk import parse_log

print(Counter(r["status"] for r in parse_log("access.log")))
```

## Adding a new tool

1. Create `src/wltk/tools/<name>.py` defining `NAME`, `HELP`,
   `add_arguments(parser)` and `run(args) -> int` (see `tools/get_method.py`
   for a filter, `tools/top.py` for a summary). Shared helpers live in
   `src/wltk/logio.py`.
2. Add the module to a category in `CATEGORIES` in
   `src/wltk/tools/__init__.py`.
3. Add tests under `tests/`, and the tool to the table at the top of this
   README using its `HELP` text (a test checks that every tool is listed).

## Development

```bash
uv run pytest           # tests
uv run ruff format .    # format
uv run ruff check .     # lint
uv run pyrefly check    # type check
```

## License

See [LICENSE](LICENSE).
