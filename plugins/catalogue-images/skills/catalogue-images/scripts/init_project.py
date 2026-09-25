"""Set up a catalogue run: write config.json and record.csv from a product sheet.

Usage:  python scripts/init_project.py --sheet products.xlsx --tab "1-100"
        python scripts/init_project.py --sheet products.csv

The sheet needs one row per SKU. Columns are matched by header name, case
insensitive, and can be remapped in config.json afterwards:
    no / serial      -> the number you refer to a SKU by on the command line
    sku              -> the SKU code, used for folder and file names
    series           -> optional, used to pick a theme
Everything else on the row is passed to the model as product facts, so extra
columns (thread count, size, box contents) are a feature, not a problem.
"""
import argparse
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOTS = ["01_hero", "02_dimension", "03_infographic", "04_lifestyle",
         "05_wash_care", "06_closeup", "07_edge_detail", "08_comparison"]


def read_rows(sheet, tab):
    if sheet.lower().endswith((".csv", ".tsv")):
        delim = "\t" if sheet.lower().endswith(".tsv") else ","
        with open(sheet, encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f, delimiter=delim)]

    import openpyxl  # only needed for spreadsheets
    wb = openpyxl.load_workbook(sheet, read_only=True, data_only=True)
    ws = wb[tab] if tab else wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() if h is not None else f"col{i}" for i, h in enumerate(rows[0])]
    out = []
    for raw in rows[1:]:
        if not any(raw):
            continue
        out.append({header[i]: raw[i] for i in range(min(len(header), len(raw)))})
    return out


def pick(row, *names):
    for key, value in row.items():
        if key and key.strip().lower() in names:
            return value
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--tab", default=None, help="worksheet name, for xlsx")
    args = ap.parse_args()

    rows = read_rows(args.sheet, args.tab)
    records = []
    for i, row in enumerate(rows, start=1):
        sku = pick(row, "sku", "opptra sku", "sku code")
        if not sku:
            continue
        n = pick(row, "no", "no.", "s. no", "serial", "sr") or i
        facts = "; ".join(f"{k}: {v}" for k, v in row.items()
                          if v not in (None, "") and k and k.strip().lower() not in
                          ("no", "no.", "s. no", "serial", "sr"))
        records.append({
            "no": int(float(n)),
            "sku": str(sku).strip(),
            "series": str(pick(row, "series", "range", "collection") or "").strip(),
            "theme": "",          # filled by make_batch from config themes
            "status": "pending",
            "notes": "",
            "facts": facts,
        })

    config = {
        "sheet": os.path.abspath(args.sheet),
        "tab": args.tab,
        "slots": SLOTS,
        "prompt": "prompts/MASTER_PROMPT.txt",
        "product_photos": "SKU-work/{sku}",
        "themes": {
            "DEFAULT": "style/DEFAULT"
        },
        "theme_rules": [
            {"if_series_contains": "kids", "theme": "DEFAULT"}
        ],
        "max_upload_mb": 10,
        "thumb_px": 1400,
    }

    with open(os.path.join(ROOT, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    with open(os.path.join(ROOT, "record.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["no", "sku", "series", "theme", "status", "notes", "facts"])
        w.writeheader()
        w.writerows(records)

    print(f"config.json and record.csv written: {len(records)} SKUs")
    print("Next: point config.json 'themes' at your approved style folders, then")
    print("      python scripts/make_batch.py 1 2 3 4")


if __name__ == "__main__":
    main()
