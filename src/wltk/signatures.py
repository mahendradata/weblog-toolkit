"""Attack signatures matched against web server log fields."""

import re
from dataclasses import dataclass
from urllib.parse import unquote

from .logio import Fields

SCANNER_AGENTS = re.compile(
    r"sqlmap|nikto|nmap|masscan|dirbuster|gobuster|acunetix|nessus|wpscan|havij|"
    r"zgrab|nuclei|openvas|w3af|metasploit|burp",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Rule:
    """A named attack signature and the log fields it is searched in."""

    category: str
    pattern: re.Pattern[str]
    fields: tuple[str, ...]


def _rule(category: str, pattern: str, fields: tuple[str, ...] = ("url",)) -> Rule:
    """Build a rule; the pattern is matched on decoded, lowercased text."""
    return Rule(category, re.compile(pattern), fields)


RULES = (
    _rule(
        "sql-injection",
        r"union\s+(all\s+)?select|'\s*or\s+['\d]|\bor\s+1\s*=\s*1|sleep\s*\(\s*\d|"
        r"benchmark\s*\(|information_schema|waitfor\s+delay|;\s*drop\s+table",
    ),
    _rule(
        "xss",
        r"<\s*script|javascript:|\bon(?:error|load|mouseover)\s*=|alert\s*\(|"
        r"<\s*img[^>]+src",
    ),
    _rule(
        "path-traversal",
        r"\.\./|\.\.\\|/etc/(?:passwd|shadow)|boot\.ini|win\.ini|/proc/self",
    ),
    _rule(
        "command-injection",
        r"[;|`]\s*(?:cat|ls|id|wget|curl|nc|bash|sh|whoami|uname)\b(?!=)|\$\(|"
        r"/bin/(?:ba)?sh|cmd\.exe|powershell",
    ),
    _rule(
        "web-shell",
        r"(?:c99|r57|b374k|wso|webshell|shell|cmd|backdoor|eval-stdin)\.php|"
        r"[?&](?:cmd|exec|command)=|base64_decode\s*\(|eval\s*\(|passthru|phpinfo",
    ),
    _rule(
        "log4shell",
        r"\$\{\s*(?:jndi|lower|upper|env|sys)\s*:",
        ("url", "user_agent", "referer"),
    ),
    _rule(
        "sensitive-file",
        r"/\.(?:env|git|svn|htaccess|htpasswd|ds_store|aws)\b|wp-config|\.sql\b|"
        r"\.bak\b|phpmyadmin|server-status|id_rsa",
    ),
    Rule("scanner-agent", SCANNER_AGENTS, ("user_agent",)),
)

ATTACK_CATEGORIES = [rule.category for rule in RULES]


def classify(fields: Fields) -> list[str]:
    """Return the categories of every rule matching the log line's fields.

    The URL is percent-decoded twice (attackers double-encode) and ``+`` is read as
    a space; matching is case-insensitive.
    """
    return [rule.category for rule in RULES if _matches(rule, fields)]


def _matches(rule: Rule, fields: Fields) -> bool:
    """Tell whether ``rule`` matches any of its fields."""
    return any(rule.pattern.search(_decoded(fields, name)) for name in rule.fields)


def _decoded(fields: Fields, name: str) -> str:
    """Return a field lowercased, and decoded when it is the URL."""
    value = (fields.get(name) or "").lower()
    if name != "url":
        return value
    return unquote(unquote(value)).replace("+", " ")
