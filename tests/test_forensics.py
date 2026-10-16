from pathlib import Path

import pytest

from wltk.cli import main
from wltk.signatures import classify


def entry(
    host: str,
    time: str,
    request: str,
    status: int = 200,
    agent: str = "Mozilla",
    zone: str = "+0000",
) -> str:
    return (
        f'{host} - - [10/Jul/2025:{time} {zone}] "{request}" {status} 10 "-" '
        f'"{agent}"\n'
    )


def write_log(tmp_path: Path, *lines: str, name: str = "access.log") -> str:
    path = tmp_path / name
    path.write_text("".join(lines), encoding="utf-8")
    return str(path)


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- signatures -----------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "agent", "category"),
    [
        ("/p?id=1+UNION+SELECT+1,2", "x", "sql-injection"),
        ("/p?id=1%27%20or%201=1", "x", "sql-injection"),
        ("/s?q=%3Cscript%3Ealert(1)%3C/script%3E", "x", "xss"),
        ("/a/%252e%252e/etc/passwd", "x", "path-traversal"),
        ("/x?f=..%5c..%5cwindows", "x", "path-traversal"),
        ("/x?c=1;cat%20/etc/hosts", "x", "command-injection"),
        ("/uploads/c99.php", "x", "web-shell"),
        ("/", "${jndi:ldap://evil/a}", "log4shell"),
        ("/.env", "x", "sensitive-file"),
        ("/", "sqlmap/1.7", "scanner-agent"),
    ],
)
def test_classify_detects(url: str, agent: str, category: str) -> None:
    fields = {"url": url, "user_agent": agent, "referer": "-"}

    assert category in classify(fields)


@pytest.mark.parametrize(
    "url",
    ["/", "/index.html?id=5&sort=asc", "/search?q=select+a+hotel", "/a;jsessionid=1"],
)
def test_classify_ignores_normal_requests(url: str) -> None:
    assert classify({"url": url, "user_agent": "Mozilla/5.0", "referer": "-"}) == []


# --- spot attacks ---------------------------------------------------------

ATTACK = entry("6.6.6.6", "10:00:00", "GET /a?id=1+union+select+1 HTTP/1.1", 500)
NORMAL = entry("1.1.1.1", "10:00:01", "GET /index.html HTTP/1.1")


def test_find_attacks_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(tmp_path, ATTACK, NORMAL)

    code, out, _ = run(["find_attacks", log, "--csv"], capsys)

    assert code == 0
    assert out.splitlines()[1].split(",")[1:3] == ["6.6.6.6", "sql-injection"]
    assert len(out.splitlines()) == 2


def test_find_attacks_raw_and_category_filter(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = write_log(tmp_path, ATTACK, NORMAL)

    assert run(["find_attacks", log, "--raw"], capsys)[1] == ATTACK
    code, _, err = run(["find_attacks", log, "-c", "xss"], capsys)
    assert code == 1
    assert "no attack signatures" in err


def test_find_scanners(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lines = [entry("7.7.7.7", "10:00:00", f"GET /p{i} HTTP/1.1", 404) for i in range(5)]
    lines.append(entry("8.8.8.8", "10:00:00", "GET / HTTP/1.1", 200, "Nikto/2.1"))
    lines.append(NORMAL)
    log = write_log(tmp_path, *lines)

    code, out, _ = run(["find_scanners", log, "--min-404", "5", "--csv"], capsys)

    assert code == 0
    assert out.splitlines()[1:] == ["7.7.7.7,5,5,5,no", "8.8.8.8,1,1,0,yes"]


def test_find_bruteforce(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fail = "POST /wp-login.php HTTP/1.1"
    lines = [entry("9.9.9.9", f"10:00:0{i}", fail, 401) for i in range(4)]
    lines.append(entry("9.9.9.9", "10:00:09", fail, 302))
    lines.append(entry("1.1.1.1", "10:00:10", fail, 401))
    log = write_log(tmp_path, *lines)

    code, out, _ = run(["find_bruteforce", log, "--csv"], capsys)

    assert code == 0
    assert out.splitlines()[1:] == ["9.9.9.9,5,4,1,yes"]


def test_find_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lines = [
        entry("1.1.1.1", f"10:00:0{i}", "GET /crash HTTP/1.1", 500) for i in range(3)
    ]
    lines.append(entry("2.2.2.2", "10:05:00", "GET /crash HTTP/1.1", 500))
    log = write_log(tmp_path, *lines)

    code, out, _ = run(["find_errors", log, "--min", "3", "--csv"], capsys)

    assert code == 0
    assert out.splitlines()[1:] == ["2025-07-10 10:00,3,1,/crash"]


# --- reconstruct ----------------------------------------------------------


def test_timeline_sessions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(
        tmp_path,
        entry("1.1.1.1", "12:00:00", "GET /late HTTP/1.1"),
        entry("1.1.1.1", "10:00:00", "GET /first HTTP/1.1"),
        entry("1.1.1.1", "10:10:00", "GET /second HTTP/1.1"),
        entry("2.2.2.2", "10:05:00", "GET /other HTTP/1.1"),
    )

    code, out, _ = run(["timeline", log, "-i", "1.1.1.1", "--csv"], capsys)

    rows = [line.split(",") for line in out.splitlines()[1:]]
    assert code == 0
    assert [(r[1], r[4]) for r in rows] == [
        ("1", "/first"),
        ("1", "/second"),
        ("2", "/late"),
    ]


def test_first_last(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(
        tmp_path,
        entry("1.1.1.1", "10:30:00", "GET /a HTTP/1.1"),
        entry("1.1.1.1", "10:00:00", "GET /b HTTP/1.1"),
        entry("2.2.2.2", "09:00:00", "GET /c HTTP/1.1"),
    )

    code, out, _ = run(["first_last", log, "--csv"], capsys)

    assert code == 0
    assert out.splitlines()[1:] == [
        "2.2.2.2,2025-07-10T09:00:00+00:00,2025-07-10T09:00:00+00:00,0.0,1",
        "1.1.1.1,2025-07-10T10:00:00+00:00,2025-07-10T10:30:00+00:00,30.0,2",
    ]


def test_pivot_skips_crowded_urls(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = [entry("6.6.6.6", "10:00:00", "GET /shell.php HTTP/1.1")]
    lines += [entry("6.6.6.7", "10:00:01", "GET /shell.php HTTP/1.1")]
    lines += [entry(f"3.3.3.{i}", "10:00:02", "GET / HTTP/1.1") for i in range(5)]
    lines += [entry("6.6.6.6", "10:00:03", "GET / HTTP/1.1")]
    log = write_log(tmp_path, *lines)

    code, out, _ = run(
        ["pivot", log, "-i", "6.6.6.6", "--max-hosts", "3", "--csv"], capsys
    )

    assert code == 0
    assert out.splitlines()[1:] == ["6.6.6.7,1,/shell.php"]


# --- check the log itself -------------------------------------------------


def test_verify_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(tmp_path, NORMAL, entry("1.1.1.1", "10:00:30", "GET / HTTP/1.1"))

    code, out, _ = run(["verify", log], capsys)

    assert code == 0
    assert "OK: 2 lines" in out


def test_verify_finds_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = write_log(
        tmp_path,
        entry("1.1.1.1", "10:00:00", "GET /a HTTP/1.1"),
        entry("1.1.1.1", "09:00:00", "GET /b HTTP/1.1"),
        "garbage\n",
        entry("1.1.1.1", "14:00:00", "GET /c HTTP/1.1", zone="+0330"),
        entry("1.1.1.1", "18:00:00", "GET /d HTTP/1.1", zone="+0330").rstrip("\n"),
    )

    code, out, err = run(["verify", log], capsys)

    checks = [line.split()[0] for line in out.splitlines()[1:]]
    assert code == 3
    assert checks == [
        "out-of-order",
        "malformed",
        "timezone-change",
        "gap",
        "truncated",
    ]
    assert "5 problems" in err


def test_hash_and_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(tmp_path, NORMAL)
    manifest = tmp_path / "manifest.txt"

    assert main(["hash", log, "-o", str(manifest)]) == 0
    assert main(["hash", "--check", str(manifest)]) == 0
    Path(log).write_text("tampered\n", encoding="utf-8")
    code, out, err = run(["hash", "--check", str(manifest)], capsys)

    assert code == 1
    assert "FAILED" in out
    assert "do not match" in err


def test_hash_needs_files(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["hash"], capsys)[0] == 2


def test_fix_time_converts_only_the_timestamp(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    line = entry("1.1.1.1", "10:00:00", "GET /a HTTP/1.1", zone="+0330")
    log = write_log(tmp_path, line, "garbage\n")

    code, out, err = run(["fix_time", log], capsys)

    assert code == 0
    assert out == line.replace("10:00:00 +0330", "06:30:00 +0000") + "garbage\n"
    assert "1 line(s) left unchanged" in err


def test_fix_time_target_zone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = write_log(tmp_path, entry("1.1.1.1", "10:00:00", "GET /a HTTP/1.1"))

    out = run(["fix_time", log, "--tz=-05:00"], capsys)[1]

    assert "[10/Jul/2025:05:00:00 -0500]" in out


def test_fix_time_rejects_bad_zone(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["fix_time", write_log(tmp_path, NORMAL), "--tz", "mars"])


def test_merge_orders_by_time_across_timezones(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    late = entry("1.1.1.1", "10:00:00", "GET /late HTTP/1.1")
    early = entry("2.2.2.2", "10:00:00", "GET /early HTTP/1.1", zone="+0100")
    a = write_log(tmp_path, late, name="a.log")
    b = write_log(tmp_path, early, "orphan line\n", name="b.log")

    out = run(["merge", a, b], capsys)[1]

    assert out.splitlines(keepends=True) == [early, "orphan line\n", late]
