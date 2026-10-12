# backup-monitor-telegram

[![CI](https://github.com/andriarezki/backup-monitor-telegram/actions/workflows/ci.yml/badge.svg)](https://github.com/andriarezki/backup-monitor-telegram/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

**A backup that fails silently is worse than no backup.** This small tool checks every night that your backups are *fresh* and *not empty*, and sends one short summary to Telegram, so you know about a problem before anyone needs a restore.

```
🔴 Nightly backups: 1 of 2 FAILED
✘ Website files: last backup 72 h ago (site.tar.gz)
✔ Database dump: 2.9 MB, 0.0 h ago
```

## Features

- Checks any number of backup folders: newest matching file, maximum age, minimum size
- Recursive search (works with `2026/10/12/dump.sql.gz` layouts, NAS and mounted shares)
- One Telegram message per run, failures listed first
- `notify: "failures"` mode: stay quiet when everything is fine
- Exit code `1` on failure, so it also works with cron mail, CI or other monitors
- Pure Python standard library: copy one file, no `pip install`
- Unit tested on Python 3.9 and 3.12

## Quick start

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather) and get your chat ID (send a message to the bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates`).
2. Copy the example config and edit the targets:

```bash
git clone https://github.com/andriarezki/backup-monitor-telegram.git
cd backup-monitor-telegram
cp config.example.json config.json
python3 backup_monitor.py config.json --dry-run     # check and print only
```

3. Run it every morning with cron:

```cron
# 06:00 every day
0 6 * * * TELEGRAM_TOKEN=123:abc TELEGRAM_CHAT_ID=123456 /usr/bin/python3 /opt/backup-monitor/backup_monitor.py /opt/backup-monitor/config.json
```

## Configuration

```json
{
  "title": "Nightly backups",
  "notify": "always",
  "targets": [
    {"name": "Database dump", "path": "/backups/db", "pattern": "*.sql.gz", "max_age_hours": 26, "min_size_bytes": 1048576},
    {"name": "Website files", "path": "/backups/www", "pattern": "*.tar.gz", "max_age_hours": 26},
    {"name": "NAS weekly",    "path": "/mnt/nas/weekly", "pattern": "*",      "max_age_hours": 192}
  ]
}
```

| Field | Default | Meaning |
|---|---|---|
| `name` | (required) | label in the report |
| `path` | (required) | folder to search (recursively) |
| `pattern` | `*` | file name pattern, e.g. `*.sql.gz` |
| `max_age_hours` | `26` | newest file must be younger than this |
| `min_size_bytes` | `1` | newest file must be at least this big (catches empty dumps) |
| `notify` | `always` | `failures` = only send when something failed |

Telegram credentials come from the `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` environment variables (recommended) or from `telegram_token` / `telegram_chat_id` in the config.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | all backups OK |
| 1 | at least one backup failed |
| 2 | config error |

## Development

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT © Andria Rezki · [andriarezki.tech](https://andriarezki.tech)
