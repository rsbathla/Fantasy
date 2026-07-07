#!/usr/bin/env python3
"""brain_pull.py — pull recent tweets from your tracked handles via twitterapi.io, extract the
article/video links, and print the NEW ones (deduped against the vault manifest) as JSON.

Reads handles from x_handles.txt (the repo). API key from env TWITTERAPI_IO_KEY (never your X token).
No network dependency beyond the twitterapi.io GET. YouTube/podcast → video; other pages → article;
X-native/social/image links are skipped for now.

  export TWITTERAPI_IO_KEY=...            # your twitterapi.io key
  python3 brain_pull.py --vault ~/Downloads/NFL-Brain [--pages 1]
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import brain_common as bc

API = "https://api.twitterapi.io/twitter/user/last_tweets"
VIDEO_HOSTS = ("youtube.com", "youtu.be", "podcasts.apple.com", "open.spotify.com/episode",
               "spotify.com/episode", "art19.com", "megaphone.fm", "omny.fm", "soundcloud.com",
               "pdst.fm", "simplecast.com")
SKIP_HOSTS = ("t.co", "twitter.com", "x.com", "instagram.com", "tiktok.com", "facebook.com",
              "threads.net", "linktr.ee", "draftkings.com", "fanduel.com", "underdogfantasy.com")


def classify(url):
    u = url.lower()
    if any(h in u for h in VIDEO_HOSTS):
        return "video"
    if any(h in u for h in SKIP_HOSTS):
        return None
    if re.search(r"\.(jpg|jpeg|png|gif|mp4|webp)(\?|$)", u):
        return None
    if not u.startswith("http"):
        return None
    return "article"


def api_get(username, cursor, key):
    q = urllib.parse.urlencode({"userName": username, "cursor": cursor, "includeReplies": "false"})
    req = urllib.request.Request(f"{API}?{q}", headers={"X-API-Key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load_handles(path):
    out = []
    for line in open(path):
        h = line.strip().lstrip("@")
        if h and not h.startswith("#"):
            out.append(h.split()[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--handles-file", default=None)
    ap.add_argument("--pages", type=int, default=1, help="pages/handle (20 tweets each); 1 is plenty for daily")
    ap.add_argument("--repo", default=None)
    a = ap.parse_args()
    repo = bc.repo_root(a.repo)
    vault = os.path.expanduser(a.vault)
    key = os.environ.get("TWITTERAPI_IO_KEY")
    if not key:
        bc.log("ERROR: TWITTERAPI_IO_KEY not set in environment"); return 2

    handles = load_handles(a.handles_file or os.path.join(repo, "x_handles.txt"))
    seen = set(bc.load_manifest(vault).keys())
    out, errs, n_tw = [], [], 0
    for h in handles:
        cursor = ""
        for _ in range(max(1, a.pages)):
            try:
                d = api_get(h, cursor, key)
            except Exception as e:
                errs.append(f"@{h}: {e}"); break
            tweets = (d.get("data") or {}).get("tweets", []) or []
            n_tw += len(tweets)
            for tw in tweets:
                for u in ((tw.get("entities") or {}).get("urls") or []):
                    url = u.get("expanded_url") or u.get("url")
                    kind = classify(url) if url else None
                    if not kind or url in seen:
                        continue
                    seen.add(url)
                    out.append({"url": url, "kind": kind, "tweet_url": tw.get("url"),
                                "handle": h, "date": tw.get("createdAt", "")})
            if not d.get("has_next_page"):
                break
            cursor = d.get("next_cursor", "")
            time.sleep(0.25)
    print(json.dumps(out, indent=1))
    bc.log(f"pull: {len(handles)} handles · {n_tw} tweets · {len(out)} new links "
           f"({sum(1 for x in out if x['kind']=='video')} video / {sum(1 for x in out if x['kind']=='article')} article) · {len(errs)} errors")
    for e in errs[:5]:
        bc.log("  " + e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
