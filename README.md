# shotfactory

Generate a set of eight catalogue images per product SKU — hero, dimension,
infographic, lifestyle, wash care, close-up, edge detail, comparison — by driving
ChatGPT Work mode in Chrome from a product spreadsheet, then QC and package them
as one client-ready zip.

Built while producing 100 bedsheet SKUs (800 images) for a real client. The
failure modes listed in the skill are all ones that actually cost a run.

## Install

```
/plugin marketplace add MuhammadKhan7073/shotfactory
/plugin install shotfactory@shotfactory
```

Then just describe the job: *"generate catalogue images for the SKUs in products.xlsx"*.
Claude loads the skill and follows the playbook.

## What you need

| | |
| --- | --- |
| Claude Code | with the **Claude in Chrome** extension connected |
| ChatGPT | an account with **Work mode** and image generation (Plus or better) |
| A product sheet | one row per SKU: serial, SKU code, and the product facts |
| Product photos | 1–2 per SKU, in `SKU-work/<SKU>/` |
| An approved style set | eight images defining the layout of each slot, per theme |
| Python | 3.9+ with `pillow` and `openpyxl` |

The style set is the part that cannot be skipped. It is what keeps 100 SKUs looking
like one catalogue instead of 100 improvisations — the client approves those eight
images once, and every SKU copies their layout.

## Run

```
python scripts/init_project.py --sheet products.xlsx --tab "1-100"
# point config.json "themes" at your style folders
python scripts/make_batch.py 1 2 3 4
python scripts/check_batches.py 1 4
#   ... Claude drives the browser: attach, paste, verify, send
python scripts/collect.py 1 2 3 4
python scripts/qc_sheet.py 1 2 3 4
python scripts/make_delivery.py
```

## Two sessions (optional)

One session with 2–3 profiles is the normal setup. If you want a second Claude
session to share the setup work, `scripts/coord.py` gives the two roles separate
profiles, separate SKU ranges, timestamped per-role logs, and a lock around browser
switching — needed because selecting a browser is global and the last selector wins.
It cuts setup time; it does not raise throughput, since the ceiling is the ChatGPT
account quota.

## Throughput

About **6 SKUs per ChatGPT account per 5-hour window**, ~40 per account per week,
and 15–20 minutes per SKU regardless of how many run in parallel. With five
accounts and four tabs each, 100 SKUs is roughly a day of wall-clock time. Image
generation has its own quota, separate from the 5-hour and weekly limits, and a
banked usage reset does not restore it.

## Licence

MIT. The master prompt is included as a template — rewrite the slot definitions and
approved copy for your own product category.
