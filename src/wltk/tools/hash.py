"""``wltk hash`` - fingerprint log files and verify them later (chain of custody)."""

import argparse
import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

from ..logio import add_output_argument, write_output

NAME = "hash"
HELP = "Write a hash manifest of log files, or verify files against one"

CHUNK = 1024 * 1024


def run(args: argparse.Namespace) -> int:
    """Run the ``hash`` tool and return an exit code."""
    if args.check:
        return _check(args.check, args.algorithm)
    if not args.files:
        print("wltk: give files to hash, or --check MANIFEST", file=sys.stderr)
        return 2
    lines = [_manifest_header(args.algorithm)]
    for name in args.files:
        path = Path(name)
        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()
        lines.append(f"# {name}: {stat.st_size} bytes, modified {modified}")
        lines.append(f"{_digest(path, args.algorithm)}  {name}")
    write_output(args.output, lambda out: out.write("\n".join(lines) + "\n"))
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare the CLI arguments of the ``hash`` tool."""
    parser.add_argument("files", nargs="*", help="log files to fingerprint")
    parser.add_argument(
        "-a",
        "--algorithm",
        choices=["sha256", "sha512", "sha1", "md5"],
        default="sha256",
        help="hash algorithm (default: sha256)",
    )
    add_output_argument(parser, "the manifest")
    parser.add_argument(
        "-c",
        "--check",
        metavar="MANIFEST",
        help="verify the files listed in a manifest instead of creating one",
    )


def _manifest_header(algorithm: str) -> str:
    """Return the comment line stating when and how the manifest was made."""
    created = datetime.now(UTC).isoformat(timespec="seconds")
    return f"# wltk hash manifest ({algorithm}), created {created}"


def _digest(path: Path, algorithm: str) -> str:
    """Return the hex digest of a file, read in chunks."""
    digest = hashlib.new(algorithm)
    with path.open("rb") as file:
        while chunk := file.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _check(manifest: str, algorithm: str) -> int:
    """Verify every ``digest  name`` entry of a manifest; 1 if any file differs."""
    failures = 0
    for line in Path(manifest).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        expected, _, name = line.partition("  ")
        try:
            ok = _digest(Path(name), algorithm) == expected
        except OSError:
            ok = False
        print(f"{name}: {'OK' if ok else 'FAILED'}")
        failures += not ok
    if failures:
        print(f"wltk: {failures} file(s) do not match the manifest", file=sys.stderr)
    return 1 if failures else 0
