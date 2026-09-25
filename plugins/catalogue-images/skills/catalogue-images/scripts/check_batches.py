"""Verify prepared BATCH folders before a run, so nothing broken gets sent.

Usage:  python scripts/check_batches.py          -> every folder
        python scripts/check_batches.py 1 20     -> that range

Checks ten readable attachments under the upload limit, and a prompt that starts
and ends with its markers, carries the SKU, and has no placeholder left in it.
Exits non-zero if anything fails.
"""
import glob
import io
import os
import sys

from PIL import Image

import common


def check(folder, cfg):
    problems = []
    name = os.path.basename(folder)
    sku = name.split("_", 1)[1] if "_" in name else name

    imgs = sorted(glob.glob(os.path.join(folder, "attach_*.jpg")))
    if len(imgs) != len(cfg["slots"]) + 2:
        problems.append(f"{len(imgs)} attachments, expected {len(cfg['slots']) + 2}")
    total_mb = sum(os.path.getsize(p) for p in imgs) / 1e6
    if total_mb > cfg["max_upload_mb"]:
        problems.append(f"{total_mb:.1f} MB total, over the {cfg['max_upload_mb']} MB upload limit")
    for p in imgs:
        try:
            Image.open(p).verify()
        except Exception as exc:
            problems.append(f"{os.path.basename(p)} unreadable ({exc})")

    prompt = os.path.join(folder, "PASTE_THIS_PROMPT.txt")
    if not os.path.isfile(prompt):
        problems.append("no PASTE_THIS_PROMPT.txt")
        return sku, problems
    text = io.open(prompt, encoding="utf-8").read().strip()
    if not text.startswith("BEGIN MASTER PROMPT"):
        problems.append("prompt does not start with BEGIN MASTER PROMPT")
    if not text.endswith("END MASTER PROMPT"):
        problems.append("prompt does not end with END MASTER PROMPT")
    if "{{PRODUCT_ROW}}" in text:
        problems.append("row placeholder was never filled in")
    if sku not in text:
        problems.append("SKU missing from the prompt")
    return sku, problems


def main(args):
    cfg = common.config()
    lo, hi = (int(args[0]), int(args[1])) if len(args) == 2 else (0, 10 ** 6)
    folders = sorted(glob.glob(os.path.join(common.ROOT, "BATCH", "[0-9]*_*")))
    folders = [f for f in folders if lo <= int(os.path.basename(f).split("_")[0]) <= hi]
    if not folders:
        raise SystemExit("no batch folders in that range")

    bad = 0
    for folder in folders:
        n = os.path.basename(folder).split("_")[0]
        sku, problems = check(folder, cfg)
        if problems:
            bad += 1
            print(f"{n} {sku}: FAIL - {'; '.join(problems)}")
    print(f"{len(folders) - bad}/{len(folders)} batch folders ready")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
