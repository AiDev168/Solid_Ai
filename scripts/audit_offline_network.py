"""Static audit for unintended outbound network access in Solid_Ai source.

Usage:
    python scripts/audit_offline_network.py

The audit intentionally ignores Markdown/docs, .git, virtual environments, caches and
sample/binary artifacts. HTTP usage is permitted only when every literal URL is loopback.
Dynamic network destinations cannot be proven statically; run the offline GUI launcher for
process-level enforcement in Python.
"""

from __future__ import annotations

import ipaddress
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "bin", "obj"}
SOURCE_SUFFIXES = {".py", ".cs", ".ps1", ".cmd", ".bat", ".js", ".ts", ".tsx", ".jsx"}
URL_RE = re.compile(r"https?://[^\s'\"`<>\\)]+", re.IGNORECASE)


def is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        return False
    host = parsed.hostname.strip("[]").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def iter_sources():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def main() -> int:
    violations: list[str] = []
    inspected = 0
    for path in iter_sources():
        inspected += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            violations.append(f"READ_ERROR {path}: {exc}")
            continue
        for url in URL_RE.findall(text):
            clean = url.rstrip(".,;:)"])}
            if not is_loopback_url(clean):
                violations.append(f"REMOTE_URL {path.relative_to(ROOT)}: {clean}")

    print(f"offline-network-audit: inspected {inspected} source files")
    if violations:
        print("FAIL")
        for item in violations:
            print(item)
        return 1
    print("PASS: no non-loopback URL literals found in source files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
