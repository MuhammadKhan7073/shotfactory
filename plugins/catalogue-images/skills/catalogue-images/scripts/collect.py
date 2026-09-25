"""Validate, file and log finished SKUs downloaded from ChatGPT.

Usage:  python scripts/collect.py 1 2 3 4
        python scripts/collect.py --all        -> every SKU not yet done

For each SKU it takes the newest Downloads/<SKU>*.zip (falling back through older
ones slot by slot, which rescues a run whose first ZIP was truncated), keeps only
images that open cleanly at the expected size, and files a SKU whose full set is
present. Partial sets are reported and left alone.
"""
import glob
import io
import os
import sys
import zipfile

from PIL import Image

import common

DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
SIZE = (2000, 2000)


def harvest(sku, slots):
    """Best available image per slot, newest ZIP first."""
    found = {}
    zips = sorted(glob.glob(os.path.join(DOWNLOADS, f"{sku}*.zip")), key=os.path.getmtime)
    for path in reversed(zips):
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                for slot in slots:
                    if slot in found:
                        continue
                    hit = [x for x in names if os.path.basename(x) == f"{sku}_{slot}.jpg"]
                    if not hit:
                        continue
                    data = z.read(hit[0])
                    try:
                        Image.open(io.BytesIO(data)).verify()
                        if Image.open(io.BytesIO(data)).size == SIZE:
                            found[slot] = data
                    except Exception:
                        pass  # corrupt member, try an older ZIP
        except zipfile.BadZipFile:
            continue
    return found, len(zips)


def main(args):
    slots = common.slots()
    rows = common.records()
    if args == ["--all"]:
        targets = [r for r in rows if not common.is_done(r)]
    else:
        targets = common.by_number(rows, args)

    for row in targets:
        sku = row["sku"]
        found, n_zips = harvest(sku, slots)
        if not n_zips:
            print(f"{row['no']:>3} {sku}: no zip in Downloads")
            continue
        if len(found) < len(slots):
            missing = [s for s in slots if s not in found]
            print(f"{row['no']:>3} {sku}: only {len(found)}/{len(slots)} usable - missing {', '.join(missing)}")
            row["notes"] = f"partial: missing {','.join(missing)}"
            continue

        dest = common.completed_dir(row)
        os.makedirs(dest, exist_ok=True)
        for slot, data in found.items():
            open(os.path.join(dest, f"{sku}_{slot}.jpg"), "wb").write(data)
        row["status"] = "completed"
        row["notes"] = ""
        print(f"{row['no']:>3} {sku}: OK, {len(slots)} x {SIZE[0]}x{SIZE[1]} JPEG")

    common.save(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
