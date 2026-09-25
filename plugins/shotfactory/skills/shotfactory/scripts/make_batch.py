"""Build ready-to-send folders for a batch of SKUs.

Usage:  python scripts/make_batch.py 1 2 3 4

For each number this writes  BATCH/NN_<SKU>/  containing
    attach_01_product.jpg ...            the product's own photos
    attach_XX_style_<THEME>_<slot>.jpg   the approved style set for its theme
    PASTE_THIS_PROMPT.txt                the master prompt with this row filled in
Attach every attach_* file, paste the prompt, send.
"""
import io
import os
import shutil
import sys

from PIL import Image

import common

PLACEHOLDER = "{{PRODUCT_ROW}}"


def theme_for(row, cfg):
    series = (row.get("series") or "").lower()
    for rule in cfg.get("theme_rules", []):
        needle = str(rule.get("if_series_contains", "")).lower()
        if needle and needle in series:
            return rule["theme"]
    return row.get("theme") or next(iter(cfg["themes"]))


def prompt_body(cfg):
    path = os.path.join(common.ROOT, cfg["prompt"])
    text = io.open(path, encoding="utf-8").read()
    if PLACEHOLDER not in text:
        raise SystemExit(f"{cfg['prompt']} has no {PLACEHOLDER} placeholder")
    return text


def main(numbers):
    cfg = common.config()
    rows = common.records()
    body = prompt_body(cfg)
    out_root = os.path.join(common.ROOT, "BATCH")
    os.makedirs(out_root, exist_ok=True)

    for row in common.by_number(rows, numbers):
        sku = row["sku"]
        theme = theme_for(row, cfg)
        style_dir = os.path.join(common.ROOT, cfg["themes"][theme])
        photo_dir = os.path.join(common.ROOT, cfg["product_photos"].format(sku=sku))
        dst = os.path.join(out_root, f"{int(row['no']):02d}_{sku}")
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)

        i = 1
        photos = sorted(x for x in os.listdir(photo_dir)) if os.path.isdir(photo_dir) else []
        if not photos:
            print(f"{row['no']:>3} {sku}: NO PRODUCT PHOTOS in {photo_dir}")
            continue
        for name in photos:
            shutil.copy(os.path.join(photo_dir, name), os.path.join(dst, f"attach_{i:02d}_product.jpg"))
            i += 1

        style_files = sorted(os.listdir(style_dir))
        for slot in cfg["slots"]:
            hit = [x for x in style_files if slot in x]
            if not hit:
                raise SystemExit(f"style set {theme} is missing a file for slot {slot}")
            # A style image is a layout reference, so 1400 px is plenty, and it keeps
            # all ten attachments inside one browser upload (10 MB bridge limit).
            im = Image.open(os.path.join(style_dir, hit[0])).convert("RGB")
            im.thumbnail((cfg["thumb_px"], cfg["thumb_px"]))
            im.save(os.path.join(dst, f"attach_{i:02d}_style_{theme}_{slot}.jpg"), "JPEG", quality=88)
            i += 1

        filled = body.replace(PLACEHOLDER, row.get("facts", ""))
        io.open(os.path.join(dst, "PASTE_THIS_PROMPT.txt"), "w",
                encoding="utf-8", newline="\n").write(filled)

        row["theme"] = theme
        print(f"{row['no']:>3}  {sku}  {theme:8} {i - 1} attachments")

    common.save(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
