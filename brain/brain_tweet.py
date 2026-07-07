#!/usr/bin/env python3
"""brain_tweet.py — capture high-signal TWEETS themselves (not just their links) into the vault.

Complements brain_ingest (which handles article/video links). This grabs the take in the tweet
body — camp notes, usage reads, injuries, and especially CHARTS/images — from your tracked handles,
resolves players/teams, downloads any images, and writes a short backlinked note in Tweets/.

Relevance gate (your call): keep intel / injuries / usage / role / news, anything with a CHART or
image, and any comparison that carries a best-ball angle. Skip bare comparisons and polls with no
best-ball significance. Everything skipped is counted, never silently dropped.

  export TWITTERAPI_IO_KEY=...
  python3 brain/brain_tweet.py --vault ~/Downloads/NFL-Brain [--pages 1]              # daily
  python3 brain/brain_tweet.py --vault ~/Downloads/NFL-Brain --since 2026-05-15       # backfill (all handles)
  python3 brain/brain_tweet.py --vault ~/Downloads/NFL-Brain --handle FantasyPtsData --since 2026-05-15
  python3 brain/brain_tweet.py --vault ~/Downloads/NFL-Brain --dump 3                 # inspect raw API shape
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

# a best-ball / tournament roster-construction angle rescues an otherwise-comparative tweet
BEST_BALL_SIGNAL = (
    "best ball", "bestball", "best-ball", "stack", "correlat", "bring-back", "bringback",
    "ceiling", "spike week", "spike-week", "advance rate", "adp", "value pick", "tournament",
    "gpp", "leverage", "roster construction", "zero rb", "hero rb", "zero-rb", "hero-rb",
    "draft capital", "late round", "late-round", "underdog", "drafters", "exposure", "onslaught",
    "playoff weeks", "weeks 15", "week 16", "week 17", "dynasty", "rookie draft", "rounds",
)
# advanced-stat vocabulary — a tweet grounded in these is signal, even if it's comparative
ADVANCED_METRICS = (
    "target share", "tgt share", "targets per route", "tprr", "yprr", "yards per route",
    "adot", "average depth of target", "air yards", "ay share", "wopr", "racr", "target rate",
    "route participation", "route rate", "routes run", "snap share", "snap count", "snap %",
    "epa", "cpoe", "proe", "pass rate over expected", "success rate", "pff", "dvoa",
    "red zone target", "rz target", "end zone target", "ez target", "carry share", "opportunity share",
    "yards after catch", "yaco", "missed tackles forced", "rush yards over expected", "ryoe",
    "explosive rate", "juke rate", "separation", "contested catch", "pressure rate", "time to throw",
    "high-value touches", "yptouch", "first read", "team target share", "designed touches",
    "any/a", "fpg", "xfp", "play action", "play-action", "personnel", "scramble rate",
)
# markers of a bare comparison / poll (skipped unless a best-ball / metric angle or chart is present)
COMPARISON_SIGNAL = (
    "would you rather", "rather have", "who would you", "who do you want", "who's better",
    "whos better", " vs ", " vs. ", "pick one", "better than", "ranking", "tiers", "rank these",
    "draft first", "take first", " or bust", "poll:",
)
# obvious promo / house-keeping that is never intel
JUNK_TWEET = ("giveaway", "promo code", "use code", "sign up", "download the app", "link in bio",
              "sponsored", "#ad ", "deposit bonus", "gambling problem", "smash that subscribe",
              "retweet to", "like and rt", "% off", "cancel your", "off any", "off your", "discount code")
# mixed-sport authors leak MLB/NBA content; charts were the worst offender (has_media keeps
# unconditionally, so a Mariners pitcher chart sailed in 2026-07-05). Sport terms chosen to
# avoid NFL collisions (no team names — Giants/Cardinals/Panthers are shared across leagues).
OTHER_SPORT = ("mlb", "baseball", "pitcher", "batter", "inning", "strikeout", "home run",
               "fastball", "bullpen", "shortstop", "woba", "xwoba", "exit velo", "slugging",
               "on-base", "wnba", " nba", "3-pointer", "rebounds per", "nhl", "puck",
               "power play", "hat trick", "clean sheet")
NFL_RESCUE = ("nfl", "fantasy football", "best ball", "bestball", "underdog", "draftkings")


def load_handles(path):
    out = []
    for line in open(path):
        h = line.strip().lstrip("@")
        if h and not h.startswith("#"):
            out.append(h.split()[0])
    return out


def api_get(username, cursor, key):
    q = urllib.parse.urlencode({"userName": username, "cursor": cursor, "includeReplies": "false"})
    req = urllib.request.Request(f"{API}?{q}", headers={"X-API-Key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


ADV_API = "https://api.twitterapi.io/twitter/tweet/advanced_search"


def adv_get(query, cursor, key):
    q = urllib.parse.urlencode({"query": query, "queryType": "Latest", "cursor": cursor})
    req = urllib.request.Request(f"{ADV_API}?{q}", headers={"X-API-Key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def to_unix(datestr):
    from datetime import datetime, timezone
    return int(datetime.strptime(datestr, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def iter_tweets(handle, key, pages, since_unix, max_pages):
    """Yield tweets for a handle: date-bounded advanced_search if since_unix else recent last_tweets."""
    cursor = ""
    if since_unix:
        query = f"from:{handle} since_time:{since_unix}"
        for _ in range(max_pages):
            d = adv_get(query, cursor, key)
            for tw in (d.get("tweets", []) or []):
                yield tw
            if not d.get("has_next_page"):
                break
            cursor = d.get("next_cursor", "") or ""
            time.sleep(0.3)
    else:
        for _ in range(max(1, pages)):
            d = api_get(handle, cursor, key)
            for tw in ((d.get("data") or {}).get("tweets", []) or []):
                yield tw
            if not d.get("has_next_page"):
                break
            cursor = d.get("next_cursor", "") or ""
            time.sleep(0.25)


def _bare_text(text):
    """True if the text is essentially just a link/emoji (no real words) — a content-free chart."""
    t = re.sub(r"https?://\S+", "", text)
    t = re.sub(r"@\w+", "", t)
    return len(re.sub(r"[^a-z]", "", t.lower())) < 8


def _content(tw):
    """Follow a retweet to the original so we capture untruncated text (RT text is clipped)."""
    rt = tw.get("retweeted_tweet")
    if isinstance(rt, dict) and (rt.get("text") or rt.get("full_text") or rt.get("fullText")):
        return rt
    return tw


def tweet_text(tw):
    t = _content(tw)
    return (t.get("text") or t.get("full_text") or t.get("fullText") or "").strip()


def _media_from(obj):
    if not isinstance(obj, dict):
        return []
    buckets = []
    for path in ("extendedEntities", "extended_entities", "entities"):
        e = obj.get(path) or {}
        if isinstance(e, dict) and e.get("media"):
            buckets.append(e["media"])
    if isinstance(obj.get("media"), list):
        buckets.append(obj["media"])
    out = []
    for media in buckets:
        for m in media:
            if isinstance(m, dict) and m.get("type") in (None, "photo", "image"):
                url = m.get("media_url_https") or m.get("media_url") or m.get("url") or m.get("src")
                if url and str(url).startswith("http"):
                    out.append(url)
    return out


def media_urls(tw):
    """Photo URLs from the tweet plus anything it retweets or quotes, so RT'd/quoted charts land."""
    urls = []
    for obj in (tw, tw.get("retweeted_tweet"), tw.get("quoted_tweet")):
        urls += _media_from(obj)
    return list(dict.fromkeys(urls))


def classify(text, players, has_media):
    """Return (keep, tag, skip_reason). Charts always kept; best-ball angle rescues comparisons."""
    tl = " " + text.lower() + " "
    if any(j in tl for j in JUNK_TWEET):
        return False, None, "promo/junk"
    # other-sport gate BEFORE the media rescue — baseball charts must not ride the chart tag
    if any(s in tl for s in OTHER_SPORT) and not any(s in tl for s in NFL_RESCUE):
        return False, None, "other sport (not NFL)"
    if has_media:
        return True, "tweet/chart", None                    # images/charts are the thing you want
    if any(s in tl for s in ADVANCED_METRICS):
        return True, "tweet/metrics", None                  # advanced-stat takes are always signal
    if any(s in tl for s in BEST_BALL_SIGNAL):
        return True, "tweet/bestball", None
    # a NUMBERED LEADERBOARD ("1. ... 2. ...") is a stat ranking, not a this-vs-that poll —
    # never comparison-flag it (the Heath motion-rate leaderboard was mis-skipped on " vs ")
    is_leaderboard = bool(re.search(r"1\.\s", text) and re.search(r"2\.\s", text))
    is_comp = (not is_leaderboard) and any(c in tl for c in COMPARISON_SIGNAL)
    if not is_comp and not is_leaderboard and len(players) >= 2 and ("?" in text or " or " in tl):
        is_comp = True                                       # poll pattern: 2+ players + a choice
    if is_comp:
        return False, None, "comparison, no best-ball angle"
    return True, "tweet/intel", None


def date_from(created):
    for fmt in ("%a %b %d %H:%M:%S %z %Y",):                 # Twitter's classic format
        try:
            from datetime import datetime
            return datetime.strptime(created, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    if len(created) >= 10 and created[4] == "-":             # already ISO-ish
        return created[:10]
    return bc.now_utc().strftime("%Y-%m-%d")


def download_media(urls, vault, stem):
    import requests
    mdir = os.path.join(vault, "_media")
    os.makedirs(mdir, exist_ok=True)
    saved = []
    for i, u in enumerate(urls):
        try:
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".jpg"
            fn = f"tw_{stem}_{i}{ext}"
            r = requests.get(u, timeout=20)
            r.raise_for_status()
            with open(os.path.join(mdir, fn), "wb") as f:
                f.write(r.content)
            saved.append(fn)
        except Exception as e:
            bc.log(f"  media download failed ({u}): {e}")
    return saved


def write_tweet(vault, handle, url, text, mentions, media_files, tag, date, is_rt=False):
    quote = os.linesep.join("> " + ln for ln in (text.splitlines() or [text]))
    imgs = os.linesep.join(f"![[{fn}]]" for fn in media_files)
    rt = " · ↻ RT" if is_rt else ""
    fname = f"{date} @{handle} — {bc.slug(text, 48)}.md"
    content = f"""---
type: tweet
author: "@{handle}"
url: {url}
date: {date}
retweet: {str(is_rt).lower()}
mentions: [{bc.wikilinks(mentions)}]
media: {len(media_files)}
tags: [source/tweet, {tag}]
ingested: {bc.now_utc().isoformat(timespec='seconds')}
---

> [!quote] @{handle} · {date}{rt} · [tweet]({url})
{quote}

{imgs}

**Mentions:** {', '.join(f'[[{m}]]' for m in mentions) if mentions else '_none detected_'}
"""
    subdir = os.path.join("Tweets", date[:7] if len(date) >= 7 and date[4] == "-" else "undated")
    return bc.write_note(vault, subdir, fname, content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--handles-file", default=None)
    ap.add_argument("--handle", default=None, help="target a single handle (real run, for testing)")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--since", default=None, help="backfill from YYYY-MM-DD via date-bounded advanced search")
    ap.add_argument("--max-pages", type=int, default=200, help="page cap per handle during a --since backfill")
    ap.add_argument("--rescan", action="store_true",
                    help="ignore per-handle backfill checkpoints and re-scan history (costs API credits)")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--dump", type=int, default=0, help="debug: print raw shape of first N tweets, no ingest")
    a = ap.parse_args()
    repo = bc.repo_root(a.repo)
    vault = os.path.expanduser(a.vault)
    key = os.environ.get("TWITTERAPI_IO_KEY")
    if not key:
        bc.log("ERROR: TWITTERAPI_IO_KEY not set"); return 2
    handles = [a.handle.lstrip("@")] if a.handle else load_handles(a.handles_file or os.path.join(repo, "x_handles.txt"))
    since_unix = to_unix(a.since) if a.since else 0

    if a.dump:
        h = handles[0]
        if since_unix:
            d = adv_get(f"from:{h} since_time:{since_unix}", "", key)
            tweets = d.get("tweets", []) or []
        else:
            d = api_get(h, "", key)
            tweets = (d.get("data") or {}).get("tweets", []) or []
        print(f"top-level keys: {list(d.keys())}")
        print(f"@{h} returned {len(tweets)} tweets")
        for tw in tweets[:a.dump]:
            print("\n--- tweet keys:", sorted(tw.keys()))
            print("createdAt:", repr(tw.get("createdAt")))
            print("text:", tweet_text(tw)[:200])
            print("media_urls():", media_urls(tw))
            for p in ("extendedEntities", "extended_entities", "entities", "media"):
                if tw.get(p):
                    print(f"has {p}: yes")
        return 0

    seen = set(bc.load_manifest(vault).keys())
    # per-handle backfill checkpoints: a handle that COMPLETED a --since window is never re-scanned
    # (the manifest dedupes notes, but re-scanning still bills every page — the 2026-07-05 lesson)
    bf_path = os.path.join(vault, "_status", "backfill_state.json")
    bf = {}
    if a.since and os.path.exists(bf_path):
        try:
            bf = json.load(open(bf_path))
        except Exception:
            bf = {}
    kept, skipped, errs = [], [], []
    for hi, h in enumerate(handles, 1):
        if a.since and not a.rescan and bf.get(h, {}).get("since") == a.since:
            bc.log(f"  [{hi}/{len(handles)}] @{h}: backfill checkpoint hit — skipped (0 API calls)")
            continue
        k0, s0 = len(kept), len(skipped)
        handle_failed = False
        try:
            for tw in iter_tweets(h, key, a.pages, since_unix, a.max_pages):
                url = tw.get("url") or f"https://x.com/{h}/status/{tw.get('id', '')}"
                if url in seen:
                    continue
                # dedupe on the ORIGINAL tweet: a retweet whose source we already have adds nothing
                canon = (tw.get("retweeted_tweet") or {}).get("url") or url
                if canon != url and canon in seen:
                    seen.add(url)
                    skipped.append((url, "retweet of already-ingested tweet"))
                    continue
                seen.add(url)
                text = tweet_text(tw)
                if not text:
                    continue
                players, teams, coaches = bc.detect_entities(text, repo)
                media = media_urls(tw)
                if not media and not (players or teams or coaches):
                    continue                                  # text-only, no entity -> skip quietly
                if media and not (players or teams or coaches) and _bare_text(text):
                    skipped.append((url, "chart with no context")); continue
                keep, tag, reason = classify(text, players, bool(media))
                if not keep:
                    skipped.append((url, reason)); continue
                try:
                    stem = str(tw.get("id") or bc.slug(url, 16))
                    saved = download_media(media, vault, stem) if media else []
                    rel = write_tweet(vault, h, url, text, players + coaches + teams, saved, tag,
                                      date_from(tw.get("createdAt", "")), is_rt=bool(tw.get("retweeted_tweet")))
                    bc.mark_done(vault, url, rel)
                    if canon != url:                          # record the source so later RTs/originals dedupe
                        bc.mark_done(vault, canon, rel)
                        seen.add(canon)
                    kept.append((tag, url))
                except Exception as e:
                    errs.append(f"{url}: {e}")
        except Exception as e:
            errs.append(f"@{h}: {e}")
            handle_failed = True
        bc.log(f"  [{hi}/{len(handles)}] @{h}: +{len(kept) - k0} kept · +{len(skipped) - s0} skipped "
               f"(total {len(kept)})")
        if a.since and not handle_failed:
            bf[h] = {"since": a.since, "kept": len(kept) - k0,
                     "at": bc.now_utc().isoformat(timespec="seconds")}
            try:
                os.makedirs(os.path.dirname(bf_path), exist_ok=True)
                json.dump(bf, open(bf_path, "w"), indent=1)
            except Exception:
                pass

    by = {t: sum(1 for k, _ in kept if k == t)
          for t in ("tweet/chart", "tweet/metrics", "tweet/bestball", "tweet/intel")}
    bc.log(f"tweets: {len(kept)} kept ({by['tweet/chart']} chart / {by['tweet/metrics']} metrics / "
           f"{by['tweet/bestball']} best-ball / {by['tweet/intel']} intel) · {len(skipped)} skipped · {len(errs)} errors")
    for e in errs[:5]:
        bc.log("  " + e)
    print(json.dumps({"kept": len(kept), "skipped": len(skipped), "errors": len(errs), "by": by}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
