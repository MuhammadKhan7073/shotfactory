"""Shared helpers: config, the record file, and slot names."""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config.json")
RECORD = os.path.join(ROOT, "record.csv")
FIELDS = ["no", "sku", "series", "theme", "status", "notes", "facts"]
DONE = ("completed", "delivered")


def config():
    if not os.path.isfile(CONFIG):
        raise SystemExit("no config.json - run scripts/init_project.py first")
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def slots():
    return config()["slots"]


def records():
    with open(RECORD, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f)]


def save(rows):
    with open(RECORD, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def by_number(rows, numbers):
    want = {int(n) for n in numbers}
    return [r for r in rows if int(r["no"]) in want]


def is_done(row):
    return str(row.get("status", "")).lower().startswith(DONE)


def completed_dir(row):
    return os.path.join(ROOT, "completed", f"{int(row['no']):02d}", row["sku"])
