#!/usr/bin/env python3
"""brain_article.py — fetch a tweeted (or hand-picked) article URL, extract the readable text, and
write it into the Obsidian vault as a clean markdown source note with player/team backlinks.

Handles PAYWALLED sites by reusing your browser login (cookies) — never stored passwords:
  1. a gitignored per-domain cookie file  brain/cookies/<domain>.txt  (Netscape format), if present;
  2. otherwise live cookies read from your logged-in Chrome via browser_cookie3;
  3. otherwise an anonymous fetch (fine for free sites).
The cookie material stays on your Mac and is never printed or committed.

  python3 brain_article.py <url> --vault ~/Downloads/NFL-Brain [--star]

  --star : mark this as one of YOUR curated picks (tag #curated, status starred) so it stands out
           from the automated firehose.
"""
import argparse
import os
import sys
from urllib.parse import urlparse

import brain_common as bc

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def cookie_jar(host, cookies_dir):
    """(jar, source) — per-domain cookies.txt (exact host, then parent domain), else live CHROME
    cookies (host + parent domain merged), else anonymous. Chrome is queried directly: the generic
    browser_cookie3.load() walks every installed browser and dies on macOS when Safari's cookie
    store is privacy-blocked — taking Chrome's perfectly readable cookies down with it."""
    parts = host.split(".")
    base = ".".join(parts[-2:]) if len(parts) > 2 else host
    for dom in dict.fromkeys((host, base)):
        ck = os.path.join(cookies_dir, dom + ".txt")
        if os.path.exists(ck):
            try:
                from http.cookiejar import MozillaCookieJar
                j = MozillaCookieJar(ck); j.load(ignore_discard=True, ignore_expires=True)
                return j, f"cookies/{dom}.txt"
            except Exception as e:
                bc.log(f"  cookie file load failed ({dom}): {e}")
    try:
        import browser_cookie3
        jar = browser_cookie3.chrome(domain_name=host)
        if base != host:                       # auth cookies usually live on the PARENT domain
            try:
                for ck in browser_cookie3.chrome(domain_name=base):
                    try:
                        jar.set_cookie(ck)
                    except Exception:
                        pass
            except Exception:
                pass
        return jar, "browser"
    except Exception as e:
        bc.log(f"  Chrome cookies unavailable ({type(e).__name__}: {str(e)[:90]}) — fetching anonymously")
        return None, "anonymous"


def fetch_html(url, cookies_dir):
    import requests
    host = urlparse(url).netloc.replace("www.", "")
    jar, src = cookie_jar(host, cookies_dir)
    r = requests.get(url, headers={"User-Agent": UA}, cookies=jar, timeout=30)
    r.raise_for_status()
    return r.text, src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--star", action="store_true", help="mark as a curated hand-pick")
    ap.add_argument("--force", action="store_true", help="re-ingest even if already in the manifest")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)
    cookies_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies")

    if bc.already_done(vault, a.url) and not a.force:
        bc.log(f"SKIP (already ingested): {a.url}")
        return 0
    if a.force and bc.already_done(vault, a.url):
        bc.log(f"re-ingesting (forced): {a.url}")

    try:
        import trafilatura
        bc.log(f"fetching … {a.url}")
        html, csrc = fetch_html(a.url, cookies_dir)
        md = trafilatura.extract(html, output_format="markdown",
                                 include_links=False, include_images=False, favor_recall=True)
        meta = trafilatura.extract_metadata(html)
    except Exception as e:
        bc.log(f"ERROR on {a.url}: {e}")
        return 1
    if not md:
        bc.log(f"ERROR: no readable body from {a.url} (paywall not unlocked? try a cookies file)")
        return 1

    title = (getattr(meta, "title", None) or "Untitled article").strip()
    outlet = (getattr(meta, "sitename", None) or urlparse(a.url).netloc.replace("www.", "")).strip()
    author = (getattr(meta, "author", None) or "").strip()
    date = (getattr(meta, "date", None) or bc.now_utc().strftime("%Y-%m-%d"))[:10]

    players, teams, coaches = bc.detect_entities(title + " " + md, repo)
    mentions = players + coaches + teams
    tags = "[source/article, curated]" if a.star else "[source/article, auto]"
    status = "starred" if a.star else "reported"

    fname = f"{date} {bc.slug(title)}.md"
    content = f"""---
type: article
title: "{title.replace('"', "'")}"
outlet: "{outlet}"
author: "{author}"
url: {a.url}
date: {date}
curated: {str(a.star).lower()}
mentions: [{bc.wikilinks(mentions)}]
tags: {tags}
status: {status}
fetched_via: {csrc}
ingested: {bc.now_utc().isoformat(timespec='seconds')}
---

# {title}{'  ⭐' if a.star else ''}

> [!cite] {outlet}{' · ' + author if author else ''} · {date}{'  · ⭐ curated pick' if a.star else ''}
> {a.url}

**Mentions:** {', '.join(f'[[{m}]]' for m in mentions) if mentions else '_none detected_'}

---

{md}
"""
    rel = bc.write_note(vault, "Sources", fname, content)
    bc.mark_done(vault, a.url, rel)
    bc.log(f"OK → {rel}  (via {csrc}; mentions: {', '.join(mentions) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
