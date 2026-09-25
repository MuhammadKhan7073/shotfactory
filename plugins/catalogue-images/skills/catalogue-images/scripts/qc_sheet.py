"""One contact sheet per batch, so a whole batch is QC'd in a single look.

Usage:  python scripts/qc_sheet.py 1 2 3 4

Each SKU becomes one row: its product photo, then every slot in order. Writes
completed/_qc_<first>-<last>.jpg and prints the path. Reading one of these costs
a quarter of what reading four separate review sheets does.
"""
import glob
import os
import sys

from PIL import Image, ImageDraw

import common

CELL = 300


def main(numbers):
    cfg = common.config()
    slots = cfg["slots"]
    rows = [r for r in common.by_number(common.records(), numbers)
            if os.path.isdir(common.completed_dir(r))]
    if not rows:
        raise SystemExit("none of those numbers are filed in completed/")

    sheet = Image.new("RGB", (CELL * (len(slots) + 1), CELL * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, row in enumerate(rows):
        sku = row["sku"]
        folder = common.completed_dir(row)
        photos = sorted(glob.glob(os.path.join(
            common.ROOT, cfg["product_photos"].format(sku=sku), "*")))
        if photos:
            im = Image.open(photos[0]).convert("RGB")
            im.thumbnail((CELL, CELL))
            sheet.paste(im, (0, r * CELL))
        for i, slot in enumerate(slots):
            p = os.path.join(folder, f"{sku}_{slot}.jpg")
            if os.path.isfile(p):
                sheet.paste(Image.open(p).convert("RGB").resize((CELL, CELL)),
                            (CELL * (i + 1), r * CELL))
        draw.rectangle([0, r * CELL, 92, r * CELL + 20], fill="black")
        draw.text((4, r * CELL + 5), f"No.{row['no']}", fill="white")

    out = os.path.join(common.ROOT, "completed",
                       f"_qc_{rows[0]['no']}-{rows[-1]['no']}.jpg")
    sheet.save(out, quality=82)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
