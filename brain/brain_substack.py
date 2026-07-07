#!/usr/bin/env python3
"""brain_substack.py — walk a Substack publication's archive and ingest matching posts through
brain_article.py (which brings the Chrome-cookie auth, entity linking, and the idempotent manifest).

Built for the Stealing Signals archive (a full season of weekly film-signal per year), but generic:
point it at any publication you subscribe to.

  # see what WOULD be ingested (no fetching of post bodies, no writes)
  python3 brain/brain_substack.py bengretch.substack.com --since 2025-08-01 --dry-run --vault ~/Downloads/NFL-Brain

  # ingest for real (rate-limited; already-ingested URLs skip instantly via the manifest)
  python3 brain/brain_substack.py bengretch.substack.com --since 2025-08-01 --vault ~/Downloads/NFL-Brain

  --match REGEX   only posts whose title matches (default: everything). e.g. --match "stealing signals"
  --until DATE    stop at this date (default: today)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

import brain_common as bc

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def archive_page(pub, offset, limit=50):
    url = f"https://{pub}/api/v1/archive?sort=new&search=&offset={offset}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if isinstance(data, dict):                     # some deployments wrap in {posts:[...]}
        data = data.get("posts") or data.get("results") or []
    return data


def post_fields(p):
    """(date 'YYYY-MM-DD', title, url, paid) defensively across archive schema variants."""
    date = (p.get("post_date") or p.get("published_at") or "")[:10]
    title = (p.get("title") or "").strip()
    url = p.get("canonical_url") or p.get("url") or ""
    paid = (p.get("audience") or "") == "only_paid"
    return date, title, url, paid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("publication", help="e.g. bengretch.substack.com")
    ap.add_argument("--vault", required=True)
    ap.add_argument("--since", required=True, help="oldest post date to ingest (YYYY-MM-DD)")
    ap.add_argument("--until", default="9999-12-31", help="newest post date to ingest (YYYY-MM-DD)")
    ap.add_argument("--match", default="", help="regex filter on the post TITLE (case-insensitive)")
    ap.add_argument("--dry-run", action="store_true", help="list matches; ingest nothing")
    ap.add_argument("--sleep", type=float, default=2.0, help="seconds between post ingests (be polite)")
    ap.add_argument("--repo", default=None)
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    pub = a.publication.replace("https://", "").strip("/")
    rx = re.compile(a.match, re.I) if a.match else None

    posts, offset = [], 0
    while True:
        try:
            page = archive_page(pub, offset)
        except Exception as e:
            bc.log(f"archive fetch failed at offset {offset}: {e}")
            break
        if not page:
            break
        stop = False
        for p in page:
            date, title, url, paid = post_fields(p)
            if not date or not url:
                continue
            if date < a.since:                      # archive is newest-first — we're past the window
                stop = True
                break
            if date > a.until:
                continue
            if rx and not rx.search(title):
                continue
            posts.append((date, title, url, paid))
        offset += len(page)
        if stop:
            break
        time.sleep(0.5)

    posts.sort()                                    # ingest oldest-first so vault dates read naturally
    bc.log(f"@{pub}: {len(posts)} matching posts {a.since} → {a.until}"
           + (f" (title ~ /{a.match}/i)" if a.match else ""))
    for date, title, url, paid in posts:
        print(f"  {date} {'🔒' if paid else '  '} {title[:80]}")
    if a.dry_run:
        print(json.dumps({"matched": len(posts), "dry_run": True}))
        return 0

    ok = fail = skipped = 0
    for i, (date, title, url, paid) in enumerate(posts, 1):
        already = bc.already_done(vault, url)
        if already:
            skipped += 1
            bc.log(f"  [{i}/{len(posts)}] SKIP (ingested): {title[:60]}")
            continue
        bc.log(f"  [{i}/{len(posts)}] ingesting: {title[:70]}")
        r = subprocess.run([sys.executable, os.path.join(HERE, "brain_article.py"), url,
                            "--vault", vault] + (["--repo", a.repo] if a.repo else []),
                           capture_output=True, text=True, timeout=180)
        tail = (r.stderr.strip().splitlines() or [""])[-1]
        if r.returncode == 0:
            ok += 1
            if "via anonymous" in tail and paid:
                bc.log(f"    ⚠️ paid post fetched ANONYMOUSLY — likely preview-only; check cookies")
        else:
            fail += 1
            bc.log(f"    ERROR: {tail[:110]}")
        time.sleep(max(0.5, a.sleep))
    bc.log(f"archive ingest: {ok} ingested · {skipped} already done · {fail} errors")
    print(json.dumps({"matched": len(posts), "ingested": ok, "skipped": skipped, "errors": fail}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
