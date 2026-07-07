#!/usr/bin/env python3
"""brain_backfill_preview.py — DRY RUN. Preview what the tweet backfill would keep vs ignore for ONE
handle since a date, using the EXACT same filter as the real run. Writes a single review file to
_status/ and nothing else — no notes, no images, no manifest changes.

  export TWITTERAPI_IO_KEY=...
  python3 brain/brain_backfill_preview.py --handle SomeAnalyst --since 2026-05-15 --vault ~/Downloads/NFL-Brain

Pick a chart/stat-heavy account for a good test. Open _status/backfill-preview-<handle>.md to review;
the media count on kept rows also confirms the search endpoint returns images.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

import brain_common as bc
import brain_tweet as bt          # reuse the real classifier / text / media / date logic

ADV_API = "https://api.twitterapi.io/twitter/tweet/advanced_search"


def adv_get(query, cursor, key):
    q = urllib.parse.urlencode({"query": query, "queryType": "Latest", "cursor": cursor})
    req = urllib.request.Request(f"{ADV_API}?{q}", headers={"X-API-Key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def snip(text, n=110):
    t = " ".join(text.split())
    return (t[:n] + "…") if len(t) > n else t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD (e.g. NFL schedule release)")
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--max-pages", type=int, default=200, help="safety cap on pages")
    a = ap.parse_args()
    key = os.environ.get("TWITTERAPI_IO_KEY")
    if not key:
        bc.log("ERROR: TWITTERAPI_IO_KEY not set"); return 2
    repo = bc.repo_root(a.repo)
    vault = os.path.expanduser(a.vault)
    since_unix = int(datetime.strptime(a.since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    h = a.handle.lstrip("@")

    rows, cursor, scanned, pages = [], "", 0, 0
    for _ in range(a.max_pages):
        d = adv_get(f"from:{h} since_time:{since_unix}", cursor, key)
        tweets = d.get("tweets", []) or []
        pages += 1
        for tw in tweets:
            scanned += 1
            text = bt.tweet_text(tw)
            if not text:
                continue
            players, teams, coaches = bc.detect_entities(text, repo)
            mentions = players + coaches + teams
            media = bt.media_urls(tw)
            date = bt.date_from(tw.get("createdAt", ""))
            is_rt = bool(tw.get("retweeted_tweet"))
            if not media and not mentions:
                rows.append(("SKIP", "no player/team", date, text, [], 0, is_rt))
                continue
            keep, tag, reason = bt.classify(text, players, bool(media))
            rows.append(("KEEP" if keep else "SKIP", tag if keep else reason, date, text, mentions, len(media), is_rt))
        if not d.get("has_next_page"):
            break
        cursor = d.get("next_cursor", "") or ""
        time.sleep(0.3)

    kept = [r for r in rows if r[0] == "KEEP"]
    skipped = [r for r in rows if r[0] == "SKIP"]
    tags = Counter(r[1] for r in kept)
    reasons = Counter(r[1] for r in skipped)
    capped = " ⚠️ hit page cap (raise --max-pages to go deeper)" if pages >= a.max_pages else ""
    n_rt = sum(1 for r in rows if r[6])
    rt_note = f" · {n_rt} retweets (↻)" if n_rt else " · no retweets in range"

    L = [f"# Backfill preview — @{h} · since {a.since}", "",
         f"> [!note] {scanned} tweets scanned · **{len(kept)} kept** · **{len(skipped)} skipped**{rt_note} · "
         f"nothing written{capped}", "",
         "**Kept by tag:** " + (", ".join(f"`{k}` {v}" for k, v in tags.most_common()) or "—"),
         "",
         "**Skipped by reason:** " + (", ".join(f"`{k}` {v}" for k, v in reasons.most_common()) or "—"),
         "", "## Kept  (↻ = retweet)"]
    for _s, tag, date, text, ment, nmed, is_rt in kept:
        img = f" 🖼️{nmed}" if nmed else ""
        rt = " ↻" if is_rt else ""
        m = ("  → " + ", ".join(f"[[{x}]]" for x in ment)) if ment else ""
        L.append(f"- `{tag}`{img}{rt} · {date} — {snip(text)}{m}")
    L += ["", "## Skipped"]
    for _s, reason, date, text, ment, nmed, is_rt in skipped:
        rt = " ↻" if is_rt else ""
        L.append(f"- `{reason}`{rt} · {date} — {snip(text)}")

    rel = bc.write_note(vault, "_status", f"backfill-preview-{h}.md", os.linesep.join(L) + os.linesep)
    bc.log(f"preview → {rel} · {scanned} scanned · {len(kept)} kept · {len(skipped)} skipped (nothing else written)")
    print(json.dumps({"scanned": scanned, "kept": len(kept), "skipped": len(skipped),
                      "retweets": n_rt, "by_tag": dict(tags), "by_reason": dict(reasons)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
