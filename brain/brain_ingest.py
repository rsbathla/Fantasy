#!/usr/bin/env python3
"""brain_ingest.py — the NFL-Brain orchestrator.

One hands-off run: pull new links from your tracked handles (brain_pull), drop junk
(promo / affiliate / URL shorteners / playlists), then ingest every surviving article
and video into the Obsidian vault. Writes _status/last-run.md as a glanceable health card.

  export TWITTERAPI_IO_KEY=...
  python3 brain/brain_ingest.py --vault ~/Downloads/NFL-Brain [--pages 1] [--model small.en]

Each piece runs as an isolated subprocess, so one bad download can't sink the whole run.
Idempotent: the capture scripts skip URLs already in the manifest, so re-runs are cheap.
"""
import argparse
import json
import os
import subprocess
import sys
from urllib.parse import urlparse

import brain_common as bc

HERE = os.path.dirname(os.path.abspath(__file__))

# --- junk filter: links that are never article/video CONTENT --------------------------------
JUNK_HOSTS = ("whop.com", "leaguetycoon.com", "onelink.me", "smart.link",
              "prizepicks.com", "pick6.draftkings.com", "sleeper.com")
JUNK_SUBSTR = ("/jobs", "/careers", "utm_campaign=promo")
# mixed-sport authors (e.g. @corbin_young21) tweet MLB/NBA links; URL slugs give the sport away
# (live case: yahoo fantasy-baseball-waiver-wire Kody Clemens article ingested 2026-07-07)
OTHER_SPORT_URL = ("baseball", "fantasy-baseball", "/mlb/", "mlb-", "fantasy-basketball",
                   "/nba/", "nba-", "/wnba/", "/nhl/", "hockey", "/soccer/", "premier-league",
                   "/golf/", "nascar", "hitters-to-stream", "pitchers-to-stream")
PLAYLIST = ("open.spotify.com/playlist", "spotify.com/playlist", "music.apple.com")
SHORTENERS = ("t.ly", "bit.ly", "tinyurl.com", "buff.ly", "rebrand.ly", "ow.ly",
              "amzn.to", "lnk.to", "spoti.fi")

ARTICLE_TIMEOUT = 120        # seconds
VIDEO_TIMEOUT = 1800         # seconds (Whisper on a long podcast is slow)


def junk_reason(url):
    """None to keep, else a short reason the link is noise (promo / shortener / playlist)."""
    u = url.lower()
    host = urlparse(u).netloc.replace("www.", "")
    if host in SHORTENERS:
        return "url shortener (target unknown)"
    if any(h in host for h in JUNK_HOSTS):
        return "promo/affiliate"
    if any(s in u for s in JUNK_SUBSTR):
        return "promo/affiliate"
    if any(p in u for p in PLAYLIST):
        return "playlist (not an episode)"
    if any(s in u for s in OTHER_SPORT_URL):
        return "other sport (not NFL)"
    return None


def run_pull(vault, pages, repo):
    cmd = [sys.executable, os.path.join(HERE, "brain_pull.py"),
           "--vault", vault, "--pages", str(pages), "--repo", repo]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.stderr:
        sys.stderr.write(r.stderr)                    # surface the pull's own summary line
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "brain_pull failed").strip().splitlines()[-1])
    return json.loads(r.stdout or "[]")


def run_tweets(vault, pages, repo):
    """Run brain_tweet as a subprocess; return its JSON summary ({} on any hiccup)."""
    cmd = [sys.executable, os.path.join(HERE, "brain_tweet.py"),
           "--vault", vault, "--pages", str(pages), "--repo", repo]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.stderr:
        sys.stderr.write(r.stderr)
    lines = (r.stdout or "").strip().splitlines()
    try:
        return json.loads(lines[-1]) if lines else {}
    except Exception:
        return {}


def capture(kind, url, vault, repo, model):
    """Run one article/video capture as an isolated subprocess. Returns (ok, last_log_line)."""
    script = "brain_video.py" if kind == "video" else "brain_article.py"
    cmd = [sys.executable, os.path.join(HERE, script), url, "--vault", vault, "--repo", repo]
    if kind == "video":
        cmd += ["--model", model]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=VIDEO_TIMEOUT if kind == "video" else ARTICLE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    tail = (r.stderr.strip().splitlines() or [""])[-1]
    return r.returncode == 0, tail


def write_card(vault, counts, ingested, skipped, errors):
    """_status/last-run.md — the glanceable health card you open in Obsidian."""
    ok = not errors
    head = "✅ OK" if ok else "⚠️ completed with errors"
    ts = bc.now_utc().strftime("%Y-%m-%d %H:%M UTC")
    L = ["# Ingest — last run", "",
         f"> [!{'success' if ok else 'warning'}] {head} · {ts}", "",
         f"- **{counts['articles']}** articles · **{counts['videos']}** videos ingested"]
    if counts.get("tweets") is not None:
        L.append(f"- **{counts['tweets']}** tweets ({counts.get('tw_chart', 0)} chart · "
                 f"{counts.get('tw_metrics', 0)} metrics · {counts.get('tw_bestball', 0)} best-ball · "
                 f"{counts.get('tw_intel', 0)} intel) · {counts.get('tw_skipped', 0)} skipped")
    L.append(f"- {counts['links']} new links · {counts['skipped']} junk skipped · {len(errors)} errors")
    if counts.get("video_overflow"):
        L.append(f"- ⚠️ {counts['video_overflow']} extra videos deferred to next run (raise --max-videos)")
    if ingested:
        L += ["", "## Ingested this run", *[f"- {x}" for x in ingested[:40]]]
        if len(ingested) > 40:
            L.append(f"- …and {len(ingested) - 40} more")
    if skipped:
        L += ["", "## Skipped (junk)", *[f"- `{u}` — {r}" for u, r in skipped[:20]]]
        if len(skipped) > 20:
            L.append(f"- …and {len(skipped) - 20} more")
    if errors:
        L += ["", "## Errors", *[f"- {e}" for e in errors[:25]]]
    bc.write_note(vault, "_status", "last-run.md", os.linesep.join(L) + os.linesep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--pages", type=int, default=1, help="pages/handle in the pull (20 tweets each)")
    ap.add_argument("--model", default="small.en", help="Whisper model for videos")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--max-videos", type=int, default=12, help="cap Whisper jobs per run (they're slow)")
    ap.add_argument("--no-tweets", action="store_true", help="skip tweet-text capture this run")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)

    try:
        links = run_pull(vault, a.pages, repo)
    except Exception as e:
        bc.log(f"FATAL: pull failed: {e}")
        write_card(vault, {"articles": 0, "videos": 0, "links": 0, "skipped": 0}, [], [], [f"pull failed: {e}"])
        return 1

    kept, skipped = [], []
    for item in links:
        reason = junk_reason(item["url"])
        if reason:
            skipped.append((item["url"], reason))
        else:
            kept.append(item)

    articles = [x for x in kept if x["kind"] == "article"]
    videos = [x for x in kept if x["kind"] == "video"]
    video_overflow = max(0, len(videos) - a.max_videos)
    videos = videos[:a.max_videos]

    ingested, errors = [], []
    n_art = n_vid = 0
    for x in articles:
        ok, msg = capture("article", x["url"], vault, repo, a.model)
        if ok:
            n_art += 1
            ingested.append(f"article · {x['url']}  _(@{x['handle']})_")
        else:
            errors.append(f"article {x['url']} — {msg}")
    for x in videos:
        ok, msg = capture("video", x["url"], vault, repo, a.model)
        if ok:
            n_vid += 1
            ingested.append(f"video · {x['url']}  _(@{x['handle']})_")
        else:
            errors.append(f"video {x['url']} — {msg}")

    tw = {}
    if not a.no_tweets:
        try:
            tw = run_tweets(vault, a.pages, repo)
        except Exception as e:
            errors.append(f"tweet capture failed: {e}")

    counts = {"articles": n_art, "videos": n_vid, "links": len(links),
              "skipped": len(skipped), "video_overflow": video_overflow}
    if not a.no_tweets:
        by = tw.get("by") or {}
        counts.update(tweets=tw.get("kept", 0), tw_skipped=tw.get("skipped", 0),
                      tw_chart=by.get("tweet/chart", 0), tw_metrics=by.get("tweet/metrics", 0),
                      tw_bestball=by.get("tweet/bestball", 0), tw_intel=by.get("tweet/intel", 0))
    write_card(vault, counts, ingested, skipped, errors)
    bc.log(f"ingest: {n_art} articles · {n_vid} videos · {counts.get('tweets', 0)} tweets · "
           f"{len(skipped)} junk · {len(errors)} errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
