---
name: shotfactory
description: Produce a set of catalogue images per product SKU (hero, dimension, infographic, lifestyle, wash care, close-up, edge detail, comparison) by driving ChatGPT Work mode in Chrome from a product spreadsheet, then validate, QC and package the results for a client. Use when someone needs marketplace or catalogue imagery in bulk for many SKUs, has product photos plus an approved style reference set, and wants the run tracked and delivered as one zip.
---

# Catalogue images in bulk

Generate eight catalogue panels per SKU by sending one long prompt plus ten reference
images into a fresh ChatGPT Work-mode chat, one chat per SKU, several chats at once
across several browser profiles. The model returns a ZIP of eight 2000x2000 JPEGs;
the scripts here validate, file, QC and package them.

This is a **browser-driving** workflow, not an API one. It needs Claude in Chrome
(`mcp__claude-in-chrome__*`) and a ChatGPT account with Work mode and image generation.

## What the user must supply

Before the first run, confirm all four exist. Do not start without them.

1. **A product sheet** (xlsx or csv) with one row per SKU. Needs at minimum a serial
   number, the SKU code, and the descriptive facts that belong in the images
   (thread count, material, size, box contents, series name).
2. **Product photos** per SKU, 1-2 each, in `SKU-work/<SKU>/ref_*.jpg`.
3. **An approved style set** per theme: eight images showing the exact layout wanted
   for each of the eight slots. The client approves these once; every SKU copies them.
4. **A ChatGPT account** (or several) with Work mode. Check the account has a **Work**
   toggle and an image-capable model. Accounts without Work mode return empty replies
   and waste the run.

Ask for anything missing rather than guessing. The style set is the one thing that
cannot be invented: without it the output drifts every time.

## Set up the run

```
python scripts/init_project.py --sheet products.xlsx --tab "1-100"
```

Writes `config.json` (paths, slot names, theme -> style folder map) and `record.csv`
(one row per SKU, status `pending`). Edit `config.json` to point the themes at the
right style folders, then:

```
python scripts/make_batch.py 1 2 3 4          # build ready-to-send folders
python scripts/check_batches.py               # verify them before sending
```

Each `BATCH/NN_<SKU>/` holds `attach_01..10` (2 product photos + 8 style images,
downscaled so all ten fit one upload) and `PASTE_THIS_PROMPT.txt`.

## The model gate, and why tabs are never reloaded

The model selection is **per conversation and does not survive a reload**: reloading
a chat drops it back to the account default, which is usually a heavier model. So:

- **Check the model button before every single send and refuse to send if it is
  wrong.** Not a warning — a hard stop. A wrong model either costs several times the
  usage per image or produces nothing at all, and you only find out 15 minutes later.
- **Never reload a working tab.** To fetch a finished ZIP, open that chat's URL in a
  separate **collector tab** (one per profile), reload *there*, click the download,
  and leave the working tabs untouched. Chat URLs are stable, so nothing is lost.
- If a working tab does get reloaded, treat its model as unset and ask the user to
  set it again before reusing that tab.

Three tabs per profile is the sweet spot. More chats at once on one account starts
producing failures rather than throughput, and the account's own quota
(~6 SKUs per 5-hour window) caps the gain anyway.

## The send loop, per tab

Work mode cannot read a .txt attachment, so the prompt goes in as inline text.

1. Open a fresh chat. Confirm **Work is on** and the model is the intended one
   (read the composer's model button; a wrong model silently produces nothing).
2. Inject a hidden file input once per tab, so the long prompt can be read from disk
   rather than typed:
   ```js
   if(!document.getElementById('cgaPromptFile')){const i=document.createElement('input');
   i.type='file';i.id='cgaPromptFile';i.setAttribute('aria-label','cga prompt file');
   i.style.position='fixed';i.style.left='-9999px';document.body.appendChild(i);}
   ```
3. `file_upload` the ten images to the composer's file input, and
   `PASTE_THIS_PROMPT.txt` to `#cgaPromptFile`.
4. Insert the text in the background (a synchronous paste of ~28k chars trips the
   45s CDP timeout):
   ```js
   window.__cgaDone=null;(async()=>{const t=await document.getElementById('cgaPromptFile').files[0].text();
   const ed=document.querySelector('#prompt-textarea')||document.querySelector('form .ProseMirror');
   ed.focus();document.execCommand('selectAll');document.execCommand('insertText',false,t);
   window.__cgaDone='ok '+t.length})();'started'
   ```
   `execCommand('insertText')` is required — a synthetic paste event is ignored.
5. **Verify, then send in the same call.** Never send blind:
   ten attachment chips, text starts `BEGIN MASTER PROMPT`, ends `END MASTER PROMPT`,
   contains this SKU, no "Pasted text.txt" chip, send button enabled.
   ```js
   const s=document.querySelector('[data-testid="send-button"]')
     ||[...document.querySelectorAll('button')].find(b=>/^Send$/i.test(b.getAttribute('aria-label')||''));
   ```
   Older layouts have no `send-button` testid — fall back to the `Send` aria-label.

## Collecting

Generation takes 15-20 minutes per SKU. Work profile by profile: send all tabs on
profile 1, move to profile 2, and by the time the last profile is loaded the first
is ready. Then:

1. Open the chat's URL in that profile's **collector tab** and reload it there. The
   "Download complete ZIP" button often does not render until a reload — and a
   reload would reset the model on a working tab, so do it in the collector.
2. Click the last such button (after a fix there are several; the newest is last).
3. If a link-confirmation panel appears, click `Open link`.
4. `python scripts/collect.py 1 2 3 4` — validates 8 x 2000x2000 JPEGs, files them
   under `completed/NN/<SKU>/`, updates `record.csv`.

## QC

```
python scripts/qc_sheet.py 1 2 3 4     # one contact sheet for the whole batch
```
Read that single image instead of four separate ones. Check per row: print and
colours match the product photo, the room is consistent across panels, icons are
**bold and filled** (thin grey line art is the most common failure), text is not
clipped, tick/cross marks are green/red.

To fix a panel, message the same chat: name the slots, say keep everything else
identical, ask for a fresh complete ZIP. Then re-collect.

## Delivery

```
python scripts/make_delivery.py            # one zip, one folder per SKU
python scripts/mark_green.py               # colour finished rows in the client sheet
```
`make_delivery.py` refuses any SKU folder that is not exactly eight 2000x2000 JPEGs,
so a half-finished SKU cannot reach the client.

## Optional: two sessions, lead and helper

Only worth it to cut **setup** time, and only when the operator wants it. It does not
raise throughput: the ceiling is the ChatGPT account quota, not how fast tabs get
loaded. A single session with 2-3 profiles is the normal setup — start there.

Selecting a browser is **global**: whichever session selects last owns it. So two
sessions must never select at the same time, and each must own its own profiles.

```
# once, in each session
python scripts/coord.py claim --role lead   --profiles <devA>,<devB> --skus 1-50
python scripts/coord.py claim --role helper --profiles <devC>,<devD> --skus 51-100

# around every browser switch
python scripts/coord.py lock   --role lead --device <devA>
#   ... select_browser, work that profile's 3 tabs, then
python scripts/coord.py unlock --role lead

# after every meaningful step
python scripts/coord.py log --role lead --sku 12 --action sent --device <devA>
python scripts/coord.py merge      # folds both logs into record.csv
```

Rules that keep it safe:

- Claim refuses overlapping profiles or overlapping SKU ranges, so the two sessions
  cannot collide by accident.
- Hold the lock for a whole profile's worth of work, not per tab. Release it before
  waiting on generation, so the other session can work while you idle.
- A lock older than four minutes is taken as abandoned, so a paused session never
  blocks the other one permanently.
- Each role writes only its own `runs/<role>.csv`; `merge` is what touches
  `record.csv`. Never have both sessions run `collect.py` on the same SKU.
- Downloads are shared and matched by SKU name, so collecting is safe in parallel.

## Failure modes, all seen in production

| Symptom | Cause and fix |
| --- | --- |
| Reply is empty, "ChatGPT said:" with nothing | Account has no Work mode, or model is a non-image one (e.g. Luna). Move the SKU to another account. |
| Tab URL stays `/c/WEB:...` then resets to `/` | The send never created a conversation. Re-send; verify the URL becomes a real `/c/<id>`. |
| "You've hit your usage limit" | Image-generation quota, separate from the 5-hour/weekly limits. A banked reset does **not** restore it. Move to another account. |
| ZIP truncated at a fixed byte size, won't open | Ask the chat to rebuild the archive from the same finished images (do not regenerate). |
| Download click does nothing | Chrome is blocking downloads for that profile — the user must allow them. |
| 9 of 10 attachments | One upload silently dropped. Re-add the missing file before sending. |
| Panels reuse the product photo's room | Add an explicit same-new-room rule; regenerate those slots. |
| Renderer times out at 45s | The tab is busy. Work one tab per call, not four. |
| Model silently back to the account default | A reload reset it. Reloads belong in the collector tab only; re-set the model before reusing a reloaded tab. |
| Two sessions keep losing the browser | Both selected at once. Take the lock (`coord.py lock`) around every switch. |

## Pacing and cost

- Roughly 6 SKUs per account per 5-hour window; ~40 per account per week.
- Check `chatgpt.com/settings/usage` before loading an account.
- Heavier models cost far more usage per image for no gain here.
- Keep tab count modest per profile; many parallel generating tabs starve the machine
  of memory and the browser bridge starts timing out.
