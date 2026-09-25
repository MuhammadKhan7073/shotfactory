"""Where the run stands, and what to load into the browser next.

Usage:  python scripts/status.py            -> progress + next assignment
        python scripts/status.py 5 4        -> plan for 5 profiles x 4 tabs

Reads record.csv only; changes nothing.
"""
import sys

import common


def main(args):
    profiles = int(args[0]) if args else 5
    tabs = int(args[1]) if len(args) > 1 else 4

    rows = common.records()
    done = [r for r in rows if common.is_done(r)]
    busy = [r for r in rows if not common.is_done(r) and r["status"] not in ("", "pending")]
    todo = [r for r in rows if r["status"] in ("", "pending")]

    print(f"done {len(done)}/{len(rows)}   in progress {len(busy)}   not started {len(todo)}")
    for r in busy:
        note = f"  {r['notes']}" if r["notes"] else ""
        print(f"  {r['no']:>3} {r['sku']}  {r['status']}{note}")

    batch = todo[:profiles * tabs]
    if not batch:
        print("\nnothing left to send")
        return
    print(f"\nnext {len(batch)} SKUs across {profiles} profiles x {tabs} tabs:")
    for i in range(profiles):
        mine = batch[i * tabs:(i + 1) * tabs]
        if mine:
            print(f"  profile {i + 1}: " + ", ".join(f"{r['no']} ({r['sku']})" for r in mine))
    rest = len(todo) - len(batch)
    if rest:
        print(f"  then {rest} more, from No. {todo[len(batch)]['no']}")


if __name__ == "__main__":
    main(sys.argv[1:])
