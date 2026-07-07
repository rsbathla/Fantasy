#!/usr/bin/env python3
"""brain_export.py — the vault -> draft-tool bridge. Walks the NFL-Brain vault and emits ONE
deterministic JSON (brain_intel.json at the repo root) keyed by display name, so the live draft
payload (engine/run_live.py) and the decision dashboard can render dated, sourced brain intel on
every scouting card. ANNOTATE-ONLY by design: nothing in this file touches sim inputs.

What it exports per PLAYER:
  claims   recent Stealing-Signals Signal/Noise claims from the page's ## Intel log (newest first)
  fwd      forward-looking 2026 claims (offseason SS installments et al., note date >= 2026-02-01)
  tw       recent tweet highlights (bestball/metrics/chart-tagged preferred) + counts incl. charts
  src26    2026 source appearances (Field Tippers, free-agency round-ups...; SS weeklies excluded
           here because they already arrive as claims)
  coach    "HC x · OC y" from web_teams.json — the SAME canon Check J audits (never hardcoded)
Plus per-TEAM (coach trio, win total, outlook, buzz) and per-COACH (buzz + 2026 sources) entries.

Idempotent and side-effect-free: reads the vault, writes one JSON. Run it after the daily ingest
(run_brain.sh calls it last), or any time:
  python3 brain/brain_export.py --vault ~/Downloads/NFL-Brain            # -> <repo>/brain_intel.json
  python3 brain/brain_export.py --vault ... --out /tmp/x.json --stats    # somewhere else + summary
"""
import argparse
import glob
import json
import os
import re
import sys

import brain_common as bc

# "- **[SS 2025 W12 · Signal]** text _(Rams 34, Buccaneers 7)_ — [[2025-11-26 Stealing Signals ...]]"
CLAIM_RE = re.compile(
    r"^- \*\*\[(?P<tag>[^\]]+?) · (?P<label>Signal|Noise)\]\*\* "
    r"(?P<text>.*?)(?:\s*_\((?P<game>[^)]*)\)_)?\s*— \[\[(?P<note>[^\]]+)\]\]\s*$")
DATE_RE = re.compile(r"^(20\d\d-\d\d-\d\d)")
TCO_RE = re.compile(r"https?://t\.co/\S+")
FWD_SINCE = "2026-02-01"          # note-date threshold for "forward-looking 2026" buckets
CAP = {"claims": 10, "fwd": 8, "tw": 6, "src26": 6, "team_tw": 4, "coach_tw": 3}
TAG_SCORE = {"tweet/bestball": 3, "tweet/metrics": 2, "tweet/chart": 1, "tweet/intel": 0}

# ---- FORWARD-LOOKING tweet curation (draft cards want 2026 direction, not retrospectives) ----
FWD_MARKERS = re.compile(
    r"\b(2026|this (?:year|season)|camp|otas?|minicamp|training camp|preseason|holdout|contract|"
    r"extension|signed|traded?|depth chart|starter|role|snaps? (?:are|will)|project(?:ed|ion|s)?|"
    r"expect(?:s|ing|ed)?|rank(?:ings?|s|ed)?|adp|draft(?:ing|s| capital)?|best ball|sleeper|"
    r"breakout|bust|league[- ]winner|target (?:share|hog)|usage|upside|value|tiers?)\b", re.I)
BACK_MARKERS = re.compile(
    r"\b(2024|2025|last (?:year|season)|past (?:two|three|few|\d+) (?:seasons|years)|career|"
    r"since 20\d\d|rookie (?:year|season)|record|previously[- ]held|dating back|all[- ]time)\b", re.I)
COMPARE_MARKERS = re.compile(
    r"\b(vs\.?|versus|edged[- ]?out|barely edged|compared? (?:to|with)|better than|worse than|"
    r"over (?:the )?(?:past|last))\b", re.I)


ADV_STAT_RE = re.compile(
    r"\b(tprr|yprr|y/rr|wopr|adot|racr|xfp|epa|cpoe|any/a|ryoe|dvoa|dyar|mtf|"
    r"target share|tgt share|targets? per|route (?:rate|win|participation|share)|routes? run|"
    r"snap (?:share|rate|count)s?|air yards?|success rate|first[- ]read|yards? (?:per|after)|"
    r"catch rate|separation|pressure rate|play[- ]action|personnel|slot rate|deep target|"
    r"red[- ]?zone|carry share|touches? per|scramble rate|dropback|receiving grade|pff grade)\b", re.I)
ADP_CHATTER_RE = re.compile(r"\b(adp|dynasty|draft(?:s|ing| capital| pick)?|rounds?|picks?|rankings?|sleepers?|values?)\b", re.I)

# ---- INJURY / AVAILABILITY vocabulary (2026-07-06 deep-audit fix; STATED PRIOR, env-revertible) ----
# The scorer had NO injury vocabulary: an ACL tear / IR stint / PED suspension scored -4 ("no numbers,
# no direction -> banter") and was DROPPED by the `_sc > 0` filter — hiding the single most
# market-moving qualitative event class from the pick-time card. This adds AVAILABILITY as a category
# (not a re-weight of the stats-first rule): an injury/availability tweet gets a strong positive so it
# clears the drop and ranks near role news, while genuine stat analysis still outranks it. This is the
# one ranking-semantics change in the 2026-07-06 pass; set BRAIN_INJURY_WEIGHT=0 to revert exactly.
INJURY_RE = re.compile(
    r"\b(acl|achilles|mcl|ucl|lcl|pcl|lisfranc|meniscus|"
    r"tore|torn|ruptured?|fractures?|fractured|broke|broken|dislocat\w*|"
    r"i\.?r\.?|injured reserve|pup|nfi|"
    r"out for (?:the )?(?:season|year)|season[- ]ending|carted|stretcher\w*|"
    r"concussion|hamstring|ankle|groin|calf|quad|hip|shoulder|foot|knee|"
    r"suspend\w*|suspension|peds?|banned|placed on|activated|designated to return|"
    r"ruled out|questionable|doubtful|dnp|did not practice|limited (?:in )?practice|"
    r"sprain\w*|strain\w*|soft tissue|re-?injur\w*|setback)\b", re.I)
BRAIN_INJURY_WEIGHT = int(os.environ.get("BRAIN_INJURY_WEIGHT", "8"))   # 0 = revert to pre-fix scoring


def tweet_base_score(text, tag_short, n_mentions):
    """Base rank of a tweet for player cards. Priority order (the user's rule, 2026-07-05):
    ADVANCED-STAT SUBSTANCE first — TPRR/YPRR/routes/usage/play-action vocabulary — because DFS
    is not ADP-driven and market chatter is not player insight. ADP/dynasty list tweets rank
    below everything stat-bearing regardless of tag, and multi-player lists get no exemption.
    AVAILABILITY news (injury/IR/suspension) is a directional category that clears the drop.
    A per-player SUBJECT bonus (player named in the first ~90 chars) is added by the caller —
    the same tweet can be the lead story for one player and a passing mention for another."""
    has_stats = bool(ADV_STAT_RE.search(text))
    has_inj = bool(BRAIN_INJURY_WEIGHT) and bool(INJURY_RE.search(text))
    s = {"metrics": 5, "chart": 4, "intel": 1, "bestball": 1}.get(tag_short, 0)
    if has_stats:
        s += 6
    if has_inj:
        s += BRAIN_INJURY_WEIGHT                 # availability is market-moving -> must clear _sc>0
    if FWD_MARKERS.search(text):
        s += 3
    if ADP_CHATTER_RE.search(text) and not has_stats:
        s -= 7                                   # pure market chatter: ADP lists, dynasty talk
    if BACK_MARKERS.search(text) and not has_stats:
        s -= 4                                   # narrative retrospectives (stat evidence stays)
    if COMPARE_MARKERS.search(text):
        s -= 2 if has_stats else 6               # stat-bearing comparisons survive but rank below
                                                 # single-subject stat tweets; bare hot takes drop
    if n_mentions >= 4:
        s -= 5                                   # list tweets are about nobody — no exemptions
    if not has_stats and not FWD_MARKERS.search(text) and not has_inj:
        s -= 5                                   # no numbers, no direction, no availability -> banter
    return s


# position words that mark a source as being ABOUT a different position (skip a "QB Tiers"
# article on a WR card); generic strategy/rankings titles carry no position word and stay
POS_TITLE_WORDS = {
    "QB": re.compile(r"\bquarterbacks?\b|\bqbs?\b", re.I),
    "RB": re.compile(r"\brunning backs?\b|\brbs?\b", re.I),
    "WR": re.compile(r"\bwide receivers?\b|\bwrs?\b", re.I),
    "TE": re.compile(r"\btight ends?\b|\btes?\b", re.I),
}


def src_pos_conflict(title, player_pos):
    if player_pos not in POS_TITLE_WORDS:
        return False
    named = [pos for pos, rx in POS_TITLE_WORDS.items() if rx.search(title)]
    return bool(named) and player_pos not in named   # title is about positions, none of them his


def parse_fm(txt):
    """Tiny frontmatter reader for the vault's simple key: value format. Returns (dict, body)."""
    if not txt.startswith("---"):
        return {}, txt
    end = txt.find("\n---", 3)
    if end < 0:
        return {}, txt
    fm = {}
    for ln in txt[3:end].splitlines():
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        fm[k.strip()] = v.strip()
    return fm, txt[end + 4:]


def fm_mentions(fm):
    return re.findall(r"\[\[([^\]]+)\]\]", fm.get("mentions", ""))


def fm_tags(fm):
    return [t.strip() for t in fm.get("tags", "").strip("[]").split(",") if t.strip()]


def quote_text(body, cap=240):
    """Tweet text = the '> ' lines after the [!quote] header, t.co stubs stripped."""
    lines = [ln[2:] for ln in body.splitlines()
             if ln.startswith("> ") and not ln.startswith("> [!quote]")]
    t = " ".join(" ".join(lines).split())
    t = TCO_RE.sub("", t).strip()
    return (t[:cap] + "…") if len(t) > cap else t


def page_display(path):
    """Display name of an entity page: its H1 (handles slugged filenames like JaMarr Chase.md)."""
    for ln in open(path, encoding="utf-8").read().splitlines():
        if ln.startswith("# "):
            return ln[2:].strip()
    return os.path.basename(path)[:-3]


def claim_entries(page_txt):
    """All Intel-log claims on a page -> [{s,t,g,n,d}], newest note-date first."""
    i = page_txt.find("## Intel log")
    if i < 0:
        return []
    zone = page_txt[i:]
    j = zone.find("\n## ", 5)
    if j > 0:
        zone = zone[:j]
    out = []
    for ln in zone.splitlines():
        m = CLAIM_RE.match(ln.strip())
        if not m:
            continue
        dm = DATE_RE.match(m["note"])
        out.append({"s": f'{m["tag"]} · {m["label"]}', "t": " ".join(m["text"].split())[:300],
                    "g": m["game"] or "", "n": m["note"], "d": dm.group(1) if dm else "",
                    "_lab": m["label"]})
    out.sort(key=lambda c: c["d"], reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None, help="default: <repo>/brain_intel.json")
    ap.add_argument("--stats", action="store_true", help="print a per-bucket summary")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)
    out_path = a.out or os.path.join(repo, "brain_intel.json")

    # ---- entity universe from the vault's own pages (display names via H1) ----
    kind_of, page_of = {}, {}
    for d, kind in (("Players", "player"), ("Teams", "team"), ("Coaches", "coach")):
        for p in sorted(glob.glob(os.path.join(vault, d, "*.md"))):
            disp = page_display(p)
            kind_of[disp] = kind
            page_of[disp] = p

    # ---- coaching canon (web_teams.json — the audited layer, never hardcoded) ----
    wt = {t["team"]: t for t in json.load(open(os.path.join(repo, "web_teams.json")))}
    coach_role = {}
    for ab, t in wt.items():
        for role in ("hc", "oc", "dc"):
            nm = (t.get(role) or "").strip()
            if nm and nm not in coach_role:
                coach_role[nm] = (ab, role.upper())

    players, teams, coaches = {}, {}, {}

    def bucket(disp):
        k = kind_of.get(disp)
        if k == "player":
            return players.setdefault(disp, {"claims": [], "fwd": [], "tw": [], "src26": [],
                                             "n_tw": 0, "n_chart": 0, "n_src": 0})
        if k == "team":
            return teams.setdefault(disp, {"tw": [], "src26": [], "n_tw": 0, "n_src": 0})
        if k == "coach":
            return coaches.setdefault(disp, {"tw": [], "src26": [], "n_tw": 0, "n_src": 0})
        return None

    # ---- 1) player pages: Intel-log claims (backward vs forward-looking 2026) ----
    n_claims = 0
    for disp, p in page_of.items():
        if kind_of[disp] != "player":
            continue
        txt = open(p, encoding="utf-8").read()
        fm, _ = parse_fm(txt)
        rec = bucket(disp)
        rec["team"] = fm.get("team", "")
        rec["pos"] = fm.get("position", "")
        cs = claim_entries(txt)
        n_claims += len(cs)
        rec["n_sig"] = sum(1 for c in cs if c["_lab"] == "Signal")
        rec["n_noise"] = sum(1 for c in cs if c["_lab"] == "Noise")
        fwd = [c for c in cs if c["d"] >= FWD_SINCE]
        back = [c for c in cs if c["d"] < FWD_SINCE]
        rec["fwd"] = [{k: c[k] for k in ("s", "t", "g", "n", "d")} for c in fwd[:CAP["fwd"]]]
        rec["claims"] = [{k: c[k] for k in ("s", "t", "g", "n", "d")} for c in back[:CAP["claims"]]]

    # ---- 2) tweets: highlights + counts per mentioned entity ----
    n_tweets = 0
    for p in sorted(glob.glob(os.path.join(vault, "Tweets", "*", "*.md"))):
        txt = open(p, encoding="utf-8").read()
        fm, body = parse_fm(txt)
        ments = fm_mentions(fm)
        if not ments:
            continue
        n_tweets += 1
        tags = fm_tags(fm)
        short = next((t.split("/", 1)[1] for t in tags if t.startswith("tweet/")), "intel")
        qt = quote_text(body)
        base = tweet_base_score(qt, short, len(ments))
        head = qt[:90].lower()
        is_chart = "tweet/chart" in tags or int(fm.get("media", "0") or 0) > 0
        for disp in ments:
            rec = bucket(disp)
            if rec is None:
                continue
            rec["n_tw"] += 1
            if "n_chart" in rec and is_chart:
                rec["n_chart"] += 1
            # SUBJECT bonus: this player named early -> the tweet is ABOUT him, not listing him
            probe = bc._base_words(disp)[-1].lower()
            sc = base + (3 if probe in head else 0)
            rec["tw"].append({"d": fm.get("date", ""), "a": fm.get("author", "").strip('"'),
                              "t": qt, "tg": short, "u": fm.get("url", ""), "_sc": sc})

    # ---- 3) sources: 2026 forward appearances (SS weeklies excluded — they arrive as claims) ----
    n_sources = 0
    for p in sorted(glob.glob(os.path.join(vault, "Sources", "*.md"))):
        fm, _ = parse_fm(open(p, encoding="utf-8").read())
        ments = fm_mentions(fm)
        if not ments:
            continue
        n_sources += 1
        title = fm.get("title", "").strip('"') or os.path.basename(p)[:-3]
        date = fm.get("date", "")
        fwd_ok = date >= FWD_SINCE and "stealing signals" not in title.lower()
        entry = {"d": date, "t": title[:120], "o": fm.get("outlet", "").strip('"')}
        for disp in ments:
            rec = bucket(disp)
            if rec is None:
                continue
            rec["n_src"] += 1
            # skip sources plainly about a different position ("QB Tiers" on a WR card)
            if fwd_ok and not src_pos_conflict(title, rec.get("pos", "")):
                rec["src26"].append(entry)

    # ---- trim + sort the per-entity lists (forward-relevance first, recency breaks ties) ----
    def finish(rec, tw_cap):
        rec["tw"].sort(key=lambda e: (e["_sc"], e["d"]), reverse=True)
        kept = [e for e in rec["tw"] if e["_sc"] > 0][:tw_cap]     # negative = retrospective/joke
        rec["tw"] = [{k: e[k] for k in ("d", "a", "t", "tg", "u")} for e in kept]
        rec["src26"].sort(key=lambda e: e["d"], reverse=True)
        rec["src26"] = rec["src26"][:CAP["src26"]]

    for disp, rec in players.items():
        finish(rec, CAP["tw"])
        t = wt.get(rec.get("team", ""))
        if t:
            rec["coach"] = f'HC {t.get("hc", "?")} · OC {t.get("oc", "?")}'
    DEF_VOCAB = re.compile(
        r"\b(defen[cs]e|defensive|DC\b|coordinator|secondary|cornerback|corner|safety|safeties|"
        r"pass rush|pass-rush|edge rusher|front seven|linebacker|coverage|blitz|man rate|"
        r"zone rate|shell|two[- ]high|single[- ]high|shadow|funnel)\b", re.I)
    for disp, rec in teams.items():
        # DEFENSE-side intel gets its own curated list (matchup research reads it separately)
        all_tw = sorted(rec["tw"], key=lambda e: (e["_sc"], e["d"]), reverse=True)
        rec["dtw"] = [{k: e[k] for k in ("d", "a", "t", "tg", "u")}
                      for e in all_tw if DEF_VOCAB.search(e["t"])][:4]
        finish(rec, CAP["team_tw"])
        ab = next((k for k, v in bc._TEAMS.items() if v[0] == disp), "")
        t = wt.get(ab)
        if t:
            rec.update({"abbr": ab, "hc": t.get("hc", ""), "oc": t.get("oc", ""),
                        "dc": t.get("dc", ""), "win_total": t.get("win_total_2026", None)})
    for disp, rec in coaches.items():
        finish(rec, CAP["coach_tw"])
        ab_role = coach_role.get(disp)
        if ab_role:
            rec["team"], rec["role"] = ab_role

    out = {"_meta": {"generated": bc.now_utc().isoformat(timespec="seconds"),
                     "vault": vault, "schema": "brain_intel v1 (annotate-only)",
                     "counts": {"players": len(players), "teams": len(teams),
                                "coaches": len(coaches), "tweets_scanned": n_tweets,
                                "sources_scanned": n_sources, "claims_seen": n_claims},
                     "caps": CAP},
           "players": players, "teams": teams, "coaches": coaches}
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    sz = os.path.getsize(out_path)
    bc.log(f"brain_export: {len(players)} players · {len(teams)} teams · {len(coaches)} coaches "
           f"· {n_claims} claims · {n_tweets} mention-tweets · {n_sources} sources → "
           f"{os.path.basename(out_path)} ({sz/1e6:.1f}MB)")
    if a.stats:
        top = sorted(players.items(), key=lambda kv: -(kv[1]["n_tw"] + len(kv[1]["claims"])))[:8]
        for nm, r in top:
            print(f"  {nm:24s} claims {len(r['claims']):>2} fwd {len(r['fwd'])} "
                  f"tw {r['n_tw']:>3} (charts {r['n_chart']}) src {r['n_src']}")
    print(json.dumps({"players": len(players), "teams": len(teams), "coaches": len(coaches),
                      "out": out_path, "bytes": sz}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
