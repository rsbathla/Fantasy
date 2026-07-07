#!/usr/bin/env python3
"""brain_book.py — ingest a PDF BOOK (FTN Almanac, Sharp's Football Preview) into the vault as
one note per TEAM CHAPTER, entity-linked, so each chapter lands on its team page's backlinks and
every player capsule reaches its player page.

Runs on the Mac (needs `pip install pymupdf` in the venv — one time). Chapter detection: a page
whose first lines contain a full team name as a heading starts that team's chapter; everything
before the first team chapter becomes a "Front matter & essays" note. If detection finds fewer
than 16 teams, nothing is written and the map is printed so we tune on the real layout.

  python3 brain/brain_book.py ~/Downloads/FTN_Almanac_2026.pdf --title "FTN Almanac 2026" \
      --vault ~/Downloads/NFL-Brain --dry-run          # detect chapters, write nothing
  ... same without --dry-run to ingest. --force re-ingests. Idempotent per chapter.
"""
import argparse
import os
import re
import sys

import brain_common as bc


def page_texts(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    return [doc[i].get_text("text") for i in range(len(doc))]


def detect_chapters(pages, team_names):
    """{team_full_name: first_page_index} — team name as a heading in a page's first lines."""
    starts = {}
    for i, txt in enumerate(pages):
        head = "\n".join(txt.splitlines()[:8]).lower()
        for tf in team_names:
            if tf in starts:
                continue
            t = tf.lower()
            # heading forms: the name on its own line, possibly ALL CAPS, optionally prefixed by a
            # year ("2026 Arizona Cardinals"), maybe followed by a record
            if re.search(r"(?m)^\s*(?:20\d\d\s+)?" + re.escape(t) + r"\s*(\(|\d|$)", head):
                starts[tf] = i
    return starts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--title", required=True, help='book title, e.g. "FTN Almanac 2026"')
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--date", default=None, help="publication date YYYY-MM-DD (default: today)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-partial", action="store_true",
                    help="ingest even if fewer than 16 team chapters were detected")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)
    pdf = os.path.expanduser(a.pdf)
    date = a.date or bc.now_utc().strftime("%Y-%m-%d")
    team_full = [v[0] for v in bc._TEAMS.values()]

    bc.log(f"reading {os.path.basename(pdf)} …")
    pages = page_texts(pdf)
    bc.log(f"{len(pages)} pages extracted")
    starts = detect_chapters(pages, team_full)

    order = sorted(starts.items(), key=lambda kv: kv[1])
    print(f"\nDetected {len(order)} team chapters:")
    for tf, p in order:
        print(f"  p.{p + 1:>4}  {tf}")
    if len(order) < 16 and not a.allow_partial:
        bc.log("fewer than 16 team chapters detected — layout needs tuning; NOTHING written. "
               "Send me this chapter map and the first heading lines of one team page.")
        return 1
    if a.dry_run:
        print('{"dry_run": true, "chapters": %d, "pages": %d}' % (len(order), len(pages)))
        return 0

    # chapter page ranges: each start -> next start (front matter = before the first)
    slug_title = bc.slug(a.title, 60)
    spans = []
    if order and order[0][1] > 0:
        spans.append(("Front matter & essays", 0, order[0][1]))
    for k, (tf, p) in enumerate(order):
        end = order[k + 1][1] if k + 1 < len(order) else len(pages)
        spans.append((tf, p, end))

    written = skipped = 0
    for name, p0, p1 in spans:
        key = f"book://{slug_title}/{bc.slug(name, 40)}"
        if bc.already_done(vault, key) and not a.force:
            skipped += 1
            continue
        body = "\n".join(pages[p0:p1]).strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        players, teams, coaches = bc.detect_entities(body[:60000], repo)
        mentions = players + coaches + (teams if name == "Front matter & essays"
                                        else sorted(set(teams) | {name} if name in team_full else set(teams)))
        is_team = name in team_full
        fname = f"{date} {slug_title} — {bc.slug(name, 40)}.md"
        content = f"""---
type: book-chapter
book: "{a.title}"
chapter: "{name}"
{f'team: "{name}"' if is_team else ''}
date: {date}
pages: {p0 + 1}-{p1}
mentions: [{bc.wikilinks(mentions)}]
tags: [source/book]
ingested: {bc.now_utc().isoformat(timespec='seconds')}
---

# {a.title} — {name}

> [!cite] {a.title} · pages {p0 + 1}–{p1} · ingested {date}

**Mentions:** {', '.join(f'[[{m}]]' for m in mentions[:60]) if mentions else '_none detected_'}

---

{body}
"""
        rel = bc.write_note(vault, "Sources", fname, content)
        bc.mark_done(vault, key, rel)
        written += 1
        bc.log(f"  OK → {rel}  ({p1 - p0} pp · {len(players)} players · {len(coaches)} coaches)")

    bc.log(f"book ingest: {written} chapters written · {skipped} already done")
    print('{"chapters_written": %d, "skipped": %d}' % (written, skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
