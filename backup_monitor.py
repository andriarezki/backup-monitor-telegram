#!/usr/bin/env python3
"""backup-monitor: check that backups are fresh and not empty, send one summary to Telegram.

    python3 backup_monitor.py config.json            # check + send
    python3 backup_monitor.py config.json --dry-run  # check + print only

Exit code: 0 all OK, 1 at least one backup failed (useful for cron/CI alerts), 2 config error.
Standard library only.
"""
import argparse
import datetime as dt
import fnmatch
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def newest(path: Path, pattern: str):
    """Newest file under path matching pattern (recursive)."""
    best = None
    for root, _dirs, files in os.walk(path):
        for f in files:
            if fnmatch.fnmatch(f, pattern):
                p = Path(root) / f
                try:
                    st = p.stat()
                except OSError:
                    continue
                if best is None or st.st_mtime > best[1].st_mtime:
                    best = (p, st)
    return best


def check(target: dict, now: dt.datetime) -> Result:
    name = target["name"]
    path = Path(target["path"])
    pattern = target.get("pattern", "*")
    max_age_h = float(target.get("max_age_hours", 26))
    min_size = int(target.get("min_size_bytes", 1))
    if not path.exists():
        return Result(name, False, f"path not found: {path}")
    found = newest(path, pattern)
    if not found:
        return Result(name, False, f"no file matching {pattern}")
    f, st = found
    age_h = (now.timestamp() - st.st_mtime) / 3600
    if age_h > max_age_h:
        return Result(name, False, f"last backup {age_h:.0f} h ago ({f.name})")
    if st.st_size < min_size:
        return Result(name, False, f"too small: {human(st.st_size)} ({f.name})")
    return Result(name, True, f"{human(st.st_size)}, {age_h:.1f} h ago")


def summary(results, title="Backup report") -> str:
    bad = [r for r in results if not r.ok]
    head = f"✅ {title}: all {len(results)} OK" if not bad else f"🔴 {title}: {len(bad)} of {len(results)} FAILED"
    lines = [head]
    for r in sorted(results, key=lambda r: r.ok):
        lines.append(f"{'✔' if r.ok else '✘'} {r.name}: {r.detail}")
    return "\n".join(lines)


def send_telegram(token: str, chat_id: str, text: str) -> None:
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=30)


def load_config(path: str) -> dict:
    cfg = json.loads(Path(path).read_text())
    if not cfg.get("targets"):
        raise ValueError("config needs a non-empty 'targets' list")
    for t in cfg["targets"]:
        for key in ("name", "path"):
            if key not in t:
                raise ValueError(f"target missing '{key}': {t}")
    return cfg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--dry-run", action="store_true", help="print the report, do not send")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config)
    except (OSError, ValueError) as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    now = dt.datetime.now()
    results = [check(t, now) for t in cfg["targets"]]
    text = summary(results, cfg.get("title", "Backup report"))
    print(text)
    only_failures = cfg.get("notify", "always") == "failures"
    if not args.dry_run and not (only_failures and all(r.ok for r in results)):
        token = os.environ.get("TELEGRAM_TOKEN") or cfg.get("telegram_token")
        chat = os.environ.get("TELEGRAM_CHAT_ID") or cfg.get("telegram_chat_id")
        if token and chat:
            send_telegram(token, str(chat), text)
        else:
            print("telegram not configured, report printed only", file=sys.stderr)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
