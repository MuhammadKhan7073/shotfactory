"""Pack every finished SKU into ONE delivery zip for the client.

Usage:  python scripts/make_delivery.py             -> all finished SKUs
        python scripts/make_delivery.py 1 50        -> only that range

Writes delivery/Catalogue_<first>-<last>_<n>SKUs.zip containing
    <SKU>/<SKU>_01_hero.jpg ... one folder per SKU, named exactly as the SKU.
A SKU is refused unless it holds every slot at the expected size, so a
half-finished product cannot reach the client.
"""
import os
import sys
import zipfile

from PIL import Image

import common

SIZE = (2000, 2000)


def problem(folder, sku, slots):
    for slot in slots:
        p = os.path.join(folder, f"{sku}_{slot}.jpg")
        if not os.path.isfile(p):
            return f"missing {slot}"
        im = Image.open(p)
        if im.size != SIZE or im.format != "JPEG":
            return f"{slot} is {im.format} {im.size}"
    return None


def main(args):
    slots = common.slots()
    lo, hi = (int(args[0]), int(args[1])) if len(args) == 2 else (0, 10 ** 6)
    rows = [r for r in common.records()
            if lo <= int(r["no"]) <= hi and os.path.isdir(common.completed_dir(r))]
    if not rows:
        raise SystemExit("nothing finished in that range")

    os.makedirs(os.path.join(common.ROOT, "delivery"), exist_ok=True)
    out = os.path.join(common.ROOT, "delivery",
                       f"Catalogue_{int(rows[0]['no']):03d}-{int(rows[-1]['no']):03d}_{len(rows)}SKUs.zip")

    packed, refused = 0, []
    # JPEGs don't compress further, so store them and keep the zip fast to open.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for row in rows:
            sku, folder = row["sku"], common.completed_dir(row)
            bad = problem(folder, sku, slots)
            if bad:
                refused.append(f"No. {row['no']} {sku}: {bad}")
                continue
            for slot in slots:
                name = f"{sku}_{slot}.jpg"
                z.write(os.path.join(folder, name), f"{sku}/{name}")
            packed += 1

    print(f"{out}\n{packed} SKU folders packed, {os.path.getsize(out) / 1e6:.0f} MB")
    for r in refused:
        print("REFUSED", r)


if __name__ == "__main__":
    main(sys.argv[1:])
