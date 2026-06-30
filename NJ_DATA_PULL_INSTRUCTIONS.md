# How to pull the NJ raw data bundle

**For Ramneik's wife:** open Claude (the Cowork/desktop app) **on the computer where the NFL
raw data lives**, make sure that computer/folder is connected, then copy-paste the block below
as your message. That's it — Claude will find the files and hand you back one zip. Send that zip
to Ramneik (he'll upload it to our chat).

If Claude says it can't see any files, tell it which folder the NFL data is in (or drag that
folder into the chat) and it'll continue.

---

## 👉 Copy-paste this to Claude:

> Hi! Please help me collect some raw NFL data files into a single zip — they're for a
> fantasy-football data pipeline, so the exact files and folder structure matter. Search this
> computer (check Downloads, Documents, Desktop, and any project/repo folders) for the **6 items**
> below and bundle them into one zip called **`nj_raw_bundle.zip`**, keeping each item inside its
> original folder path:
>
> 1. The whole **`csv` folder** located at `ffdataroma_draft_guide_export/ffdataroma/csv/`
>    (the FFDataRoma draft-guide export — a folder full of CSV files).
> 2. The whole **`nfl_pro_scraper` folder** located at `NFL-master/nfl_chat_app/app_data/nfl_pro_scraper/`.
> 3. The file **`AGG_MASTER_ALL_COVERAGES_WR.csv`** (usually in `NFL-master/AGG_COVERAGE_SHEETS_WR_LAST6/`).
> 4. The file **`AGG_MASTER_ALL_RUNTYPES_WITH_TARGETS.csv`** (usually in `NFL-master/AGG_COVERAGE_SHEETS_RB_LAST6/`).
> 5. The file **`defense_2026_matchup.json`** (usually in `dfs_review/out/`).
> 6. The file **`receivingManVsZone_2025.csv`**.
>
> Important:
> - Preserve each file's original folder path **inside** the zip (don't flatten them into one folder).
> - If you can't find one of the 6, just tell me which are missing — **do not** substitute, rename,
>   or make up any files. Real files only.
> - These are large data folders; it's fine if the zip is big. When it's ready, give me
>   `nj_raw_bundle.zip` to download.
>
> Thank you!

---

## What these 6 things are (FYI, no action needed)

They're the only non-FantasyPoints inputs the pipeline needs to do a full rebuild:
draft-guide projections (FFDataRoma), the pro-scraper app data, the WR coverage + RB run-type
aggregate sheets, the 2026 defense matchup file, and the receiving man-vs-zone sheet. Everything
else (PFF, FTN, FantasyPoints) is already pulled.

## After your wife sends the zip

Ramneik: upload `nj_raw_bundle.zip` to our chat (or drop it in your Downloads and tell me).
I'll unpack the 6 roots, run the `--full` ingest, and fold it into the dataset + profiles.
