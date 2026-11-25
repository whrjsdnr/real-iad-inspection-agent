"""Secret scan for tracked/staged files.

Reads real credential values from local config/team-share.env (never printed) and
generic patterns (DB URLs with passwords, private keys, cloud tokens). Exits 1 on hit.
Usage: python scripts/scan_secrets.py [--all-history]
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"postgresql(\+[a-z0-9]+)?://[^:]+:(?!REPLACE_ME|REPLACE|<)[^@\s'\"]+@"),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

def local_secrets() -> list[str]:
    env = ROOT / "config" / "team-share.env"
    out = []
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(("TEAM_ACCESS_TOKEN=", "DATABASE_URL_READ=")):
                value = line.split("=", 1)[1].strip()
                if value and "REPLACE" not in value:
                    out.append(value)
                    if line.startswith("DATABASE_URL_READ="):
                        from urllib.parse import urlparse
                        pw = urlparse(value).password
                        if pw:
                            out.append(pw)
    return [s for s in out if len(s) >= 8]

def scan_text(name: str, text: str, secrets: list[str]) -> list[str]:
    hits = []
    for s in secrets:
        if s in text:
            hits.append(f"real credential value in {name}")
    for p in PATTERNS:
        if p.search(text):
            hits.append(f"pattern {p.pattern[:24]}... in {name}")
    return hits

def main() -> int:
    secrets = local_secrets()
    names = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    problems: list[str] = []
    for name in names:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size > 20_000_000:
            continue
        try:
            problems += scan_text(name, path.read_text(errors="ignore"), secrets)
        except OSError:
            continue
    if "--all-history" in sys.argv:
        commits = subprocess.run(["git", "rev-list", "--all"], cwd=ROOT, capture_output=True, text=True).stdout.split()
        for c in commits:
            files = subprocess.run(["git", "ls-tree", "-r", "--name-only", c], cwd=ROOT, capture_output=True, text=True).stdout.split()
            for name in files:
                blob = subprocess.run(["git", "show", f"{c}:{name}"], cwd=ROOT, capture_output=True).stdout
                text = blob.decode(errors="ignore")
                if "config/team-share.env" in name and any(s in text for s in secrets):
                    problems.append(f"real credential in history {c}:{name}")
    seen = sorted(set(problems))
    for p in seen:
        print("HIT:", p)
    if seen:
        print(f"secret scan FAILED ({len(seen)} findings)")
        return 1
    print("secret scan passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
