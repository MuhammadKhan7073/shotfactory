"""Coordination for two Claude sessions working the same run.

One session is `lead`, the other `helper`. Each owns its own profiles and its own
SKU range, keeps its own timestamped log, and takes a short lock before touching
the browser — because selecting a browser is global: the session that selects last
owns it, so two sessions selecting at once steal it from each other.

    python scripts/coord.py claim  --role lead   --profiles dev-a,dev-b --skus 1-50
    python scripts/coord.py claim  --role helper --profiles dev-c,dev-d --skus 51-100

    python scripts/coord.py lock   --role lead --device dev-a      # before select_browser
    python scripts/coord.py unlock --role lead
    python scripts/coord.py log    --role lead --sku 12 --action sent --device dev-a
    python scripts/coord.py merge                                  # both logs -> record.csv
    python scripts/coord.py status

A lock older than --stale seconds (default 240) is treated as abandoned and taken,
so a crashed or paused session never blocks the other one for good.
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

import common

RUNS = os.path.join(common.ROOT, "runs")
CLAIMS = os.path.join(RUNS, "claims.json")
LOCK = os.path.join(RUNS, "browser.lock")
LOG_FIELDS = ["ts", "role", "no", "sku", "action", "device", "chat", "note"]
ROLES = ("lead", "helper")
# Actions that mean a SKU is finished, in the order a SKU passes through them.
TERMINAL = {"filed", "passed", "failed", "abandoned"}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log_path(role):
    return os.path.join(RUNS, f"{role}.csv")


def read_log(role):
    path = log_path(role)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_log(role, entry):
    os.makedirs(RUNS, exist_ok=True)
    path = log_path(role)
    new = not os.path.isfile(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow(entry)


def parse_range(spec):
    lo, _, hi = spec.partition("-")
    return int(lo), int(hi or lo)


def cmd_claim(a):
    os.makedirs(RUNS, exist_ok=True)
    claims = {}
    if os.path.isfile(CLAIMS):
        claims = json.load(open(CLAIMS, encoding="utf-8"))
    lo, hi = parse_range(a.skus)
    mine = [p.strip() for p in a.profiles.split(",") if p.strip()]

    for role, c in claims.items():
        if role == a.role:
            continue
        clash = set(mine) & set(c["profiles"])
        if clash:
            raise SystemExit(f"{role} already owns profile(s): {', '.join(sorted(clash))}")
        if not (hi < c["skus"][0] or lo > c["skus"][1]):
            raise SystemExit(f"{role} already owns SKUs {c['skus'][0]}-{c['skus'][1]}")

    claims[a.role] = {"profiles": mine, "skus": [lo, hi], "claimed": now()}
    json.dump(claims, open(CLAIMS, "w", encoding="utf-8"), indent=2)
    print(f"{a.role}: profiles {', '.join(mine)}   SKUs {lo}-{hi}")
    for role, c in claims.items():
        if role != a.role:
            print(f"  (other) {role}: {', '.join(c['profiles'])}  SKUs {c['skus'][0]}-{c['skus'][1]}")


def cmd_lock(a):
    os.makedirs(RUNS, exist_ok=True)
    deadline = time.time() + a.wait
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as f:
                json.dump({"role": a.role, "device": a.device, "ts": time.time(),
                           "at": now()}, f)
            print(f"lock acquired by {a.role} for {a.device}")
            return
        except FileExistsError:
            try:
                held = json.load(open(LOCK, encoding="utf-8"))
            except Exception:
                held = {"role": "?", "ts": 0}
            age = time.time() - held.get("ts", 0)
            if held.get("role") == a.role:
                print(f"lock already held by {a.role} ({age:.0f}s) - continuing")
                return
            if age > a.stale:
                os.remove(LOCK)
                print(f"took over stale lock from {held.get('role')} ({age:.0f}s old)")
                continue
            if time.time() >= deadline:
                raise SystemExit(f"busy: {held.get('role')} holds the browser "
                                 f"({age:.0f}s). Try again, or work on files meanwhile.")
            time.sleep(3)


def cmd_unlock(a):
    if not os.path.isfile(LOCK):
        print("no lock held")
        return
    held = json.load(open(LOCK, encoding="utf-8"))
    if held.get("role") != a.role and not a.force:
        raise SystemExit(f"lock belongs to {held.get('role')}; use --force to break it")
    os.remove(LOCK)
    print("lock released")


def cmd_log(a):
    append_log(a.role, {"ts": now(), "role": a.role, "no": a.sku or "", "sku": a.sku_code or "",
                        "action": a.action, "device": a.device or "", "chat": a.chat or "",
                        "note": a.note or ""})
    print(f"{a.role} {a.action} {a.sku or ''}".strip())


def cmd_merge(_a):
    """Fold both logs into record.csv: last terminal action per SKU wins."""
    latest = {}
    for role in ROLES:
        for e in read_log(role):
            if not e.get("no"):
                continue
            n = int(e["no"])
            prev = latest.get(n)
            if prev is None or e["ts"] >= prev["ts"]:
                latest[n] = e

    rows = common.records()
    changed = 0
    for row in rows:
        e = latest.get(int(row["no"]))
        if not e:
            continue
        action = e["action"]
        if action in TERMINAL:
            status = "completed" if action in ("filed", "passed") else action
        else:
            status = action
        if row["status"] != status:
            row["status"] = status
            row["notes"] = f"{e['role']} {e['ts']}" + (f" {e['note']}" if e["note"] else "")
            changed += 1
    common.save(rows)
    print(f"record.csv updated from {sum(len(read_log(r)) for r in ROLES)} log entries "
          f"({changed} rows changed)")


def cmd_status(_a):
    if os.path.isfile(CLAIMS):
        for role, c in json.load(open(CLAIMS, encoding="utf-8")).items():
            print(f"{role:7} profiles {', '.join(c['profiles'])}   SKUs {c['skus'][0]}-{c['skus'][1]}")
    if os.path.isfile(LOCK):
        held = json.load(open(LOCK, encoding="utf-8"))
        print(f"browser lock: {held['role']} on {held['device']} since {held['at']}")
    else:
        print("browser lock: free")
    for role in ROLES:
        entries = read_log(role)
        if entries:
            last = entries[-1]
            print(f"{role:7} {len(entries):>4} actions, last: {last['action']} "
                  f"{last['no']} at {last['ts']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("claim"); p.set_defaults(fn=cmd_claim)
    p.add_argument("--role", choices=ROLES, required=True)
    p.add_argument("--profiles", required=True, help="comma-separated device ids")
    p.add_argument("--skus", required=True, help="range, e.g. 1-50")

    p = sub.add_parser("lock"); p.set_defaults(fn=cmd_lock)
    p.add_argument("--role", choices=ROLES, required=True)
    p.add_argument("--device", required=True)
    p.add_argument("--wait", type=float, default=30, help="seconds to wait for a busy lock")
    p.add_argument("--stale", type=float, default=240, help="seconds before a lock is abandoned")

    p = sub.add_parser("unlock"); p.set_defaults(fn=cmd_unlock)
    p.add_argument("--role", choices=ROLES, required=True)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("log"); p.set_defaults(fn=cmd_log)
    p.add_argument("--role", choices=ROLES, required=True)
    p.add_argument("--action", required=True,
                   help="sent | generating | downloaded | filed | passed | failed | abandoned | note")
    p.add_argument("--sku", type=int, help="the sheet number")
    p.add_argument("--sku-code", dest="sku_code")
    p.add_argument("--device")
    p.add_argument("--chat")
    p.add_argument("--note")

    sub.add_parser("merge").set_defaults(fn=cmd_merge)
    sub.add_parser("status").set_defaults(fn=cmd_status)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
