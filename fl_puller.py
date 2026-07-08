#!/usr/bin/env python3
"""fl_puller.py — FantasyLabs contest OWNERSHIP puller (all contest types), via public CloudFront.

WHAT THIS GETS (reverse-engineered from terminal.fantasylabs.com's Ownership dashboard):
  Per contest, per player: field OWNERSHIP %, FantasyLabs projection, ACTUAL points, salary, team,
  position, home/away, fav/dog — PLUS team-stack and game-stack ownership. For EVERY contest type:
  main-slate Milly Maker ($20), high-roller ($4,444), Wildcat ($333), Showdown (single-game), and
  the early/afternoon-only slates. This is the real field ownership we need to (a) replace the
  ownership PROXY in backtest_leverage.py with measured numbers and (b) feed dfs_optimizer.py so it
  fades the actual field instead of just spreading shapes.

NO AUTH NEEDED. Both data hosts are public CDN caches:
  GROUP (lists a slate's contests):  https://d3ttxfuywgi7br.cloudfront.net/contests/{group_id}/
  OWNERSHIP (per contest):           https://dh5nxc6yx3kwy.cloudfront.net/contests/nfl/{YYYYMMDD}/{contest_id}/data/
The terminal app resolves date->group_id behind a login, but we don't need it: group_ids run
monotonically with date (~41/day), so we SCAN the id space, keep SportId==1 (NFL), and index by date.

RUN IT ON YOUR MAC (this cloud sandbox is walled off from fetching URLs; your Mac isn't, and the
data is public so no cookies are involved). Then I stage the CSVs back and wire them in.

  pip install requests --break-system-packages
  python3 fl_puller.py --discover                       # sanity-check parsing on a known slate
  python3 fl_puller.py --scan-dates 2024-09-01 2025-01-31   # build groups_index.json (NFL only)
  python3 fl_puller.py --pull --all-types --stacks      # pull ownership+stacks for every NFL contest
  # or filter: --pull --milly --highroller --wildcat --showdown  (mix and match)

Output: data/fantasylabs/players/{date}_{slate}_{contestId}.csv   (one row per player)
        data/fantasylabs/stacks/{date}_{slate}_{contestId}.csv    (team & game stack ownership)
Everything is resumable — re-running skips groups already scanned and contests already pulled.
"""
import argparse, csv, json, os, re, sys, time
from datetime import date, timedelta

try:
    import requests
except ImportError:
    sys.exit("need requests: pip install requests --break-system-packages")

GROUP = "https://d3ttxfuywgi7br.cloudfront.net/contests/{gid}/"
DATA = "https://dh5nxc6yx3kwy.cloudfront.net/contests/nfl/{ymd}/{cid}/data/"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "fantasylabs")
INDEX = os.path.join(OUT, "groups_index.json")

# observed (group_id, date) anchors (captured from the live app) -> piecewise-linear model
# to estimate the id window for any date 2021-2025. ~42-44 group ids created per day.
ANCHORS = sorted([
    (67547,  date(2021, 11, 21)),     # observed live (2021 season)
    (115396, date(2024, 11, 17)),
    (116312, date(2024, 12, 8)),
    (117428, date(2025, 1, 5)),
])


def gid_for(d):
    a = ANCHORS
    if d <= a[0][1]:                                  # extrapolate backward
        slope = (a[1][0] - a[0][0]) / (a[1][1] - a[0][1]).days
        return int(a[0][0] + slope * (d - a[0][1]).days)
    for (g0, d0), (g1, d1) in zip(a, a[1:]):          # interpolate between anchors
        if d0 <= d <= d1:
            slope = (g1 - g0) / (d1 - d0).days
            return int(g0 + slope * (d - d0).days)
    g0, d0 = a[-1]                                    # extrapolate forward
    slope = (a[-1][0] - a[-2][0]) / (a[-1][1] - a[-2][1]).days
    return int(g0 + slope * (d - d0).days)


def _get(url, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 404):
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


# ---------------------------------------------------------------- classify contest / slate
def slate_type(title):
    t = (title or "").lower()
    if "showdown" in t or "single game" in t or "captain" in t:
        return "showdown"
    if "afternoon" in t:
        return "afternoon"
    if "early" in t:
        return "early"
    if "primetime" in t or "night" in t or "sunday night" in t or "monday night" in t or "thursday" in t:
        return "primetime"
    return "main"


def contest_class(cd):
    """Tag a contest by the buckets you care about (from title + entry cost).

    'Millionaire Maker' runs at several entry fees every week — $20 (the big one), and a
    high-entry $555 or $4,444 version. We tag ALL of them 'milly' (entry fee kept in the CSV
    so you can split later) and also flag the high-entry ones 'highroller'.
    """
    t = (cd.get("Title") or "").lower()
    cost = cd.get("EntryCost") or 0
    tags = []
    if "millionaire" in t:
        tags.append("milly")                 # $20, $555, $4,444 — every Millionaire Maker
        if cost >= 300:
            tags.append("highroller")        # the high-entry Milly ($555 / $4,444)
    if "wildcat" in t or cost == 333:
        tags.append("wildcat")
    if slate_type(cd.get("Title")) == "showdown":
        tags.append("showdown")
    return tags


# ---------------------------------------------------------------- group recording
def _load_idx():
    os.makedirs(OUT, exist_ok=True)
    idx = json.load(open(INDEX)) if os.path.exists(INDEX) else {}
    idx.setdefault("_scanned", [])
    idx.setdefault("groups", {})
    return idx


def _record(idx, gid, target_lo=None, target_hi=None):
    """Fetch one group id and record it if it's an NFL group in range. True if recorded."""
    if str(gid) in idx["groups"]:
        return False
    j = _get(GROUP.format(gid=gid))
    if not (j and isinstance(j, list) and j and j[0].get("ContestData")):
        return False
    cd0 = j[0]["ContestData"]
    if cd0.get("SportId") != 1:
        return False
    d = (cd0.get("Date") or "")[:10]
    if target_lo and (d < target_lo or d > target_hi):
        return False
    contests = [{"id": c["ContestData"]["ContestId"], "title": c["ContestData"]["Title"],
                 "size": c["ContestData"]["ContestSize"], "cost": c["ContestData"]["EntryCost"],
                 "dg": c["ContestData"]["DraftGroupId"]} for c in j]
    idx["groups"][str(gid)] = {"date": d, "slate": slate_type(cd0.get("Title")),
                               "dg": cd0.get("DraftGroupId"), "contests": contests}
    print(f"  gid {gid}  {d}  {slate_type(cd0.get('Title')):9} "
          f"{len(contests)} contests  top='{cd0['Title'][:34]}'")
    return True


# ---------------------------------------------------------------- harvest (RECOMMENDED)
TERMINAL = "https://www.fantasylabs.com"   # placeholder; real host set below

def harvest_dates(d0, d1):
    """Resolve every date's contest groups from the terminal app's server-rendered page —
    NO login, NO id scanning. Works for every archived season (2021+). ~1 min per season."""
    idx = _load_idx()
    seen_gids = set(idx["groups"].keys())
    d = d0
    n_pages = n_new = 0
    while d <= d1:
        url = f"https://terminal.fantasylabs.com/ownership?sportId=1&date={d.month}/{d.day}/{d.year}"
        try:
            r = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0"})
            txt = r.text if r.status_code == 200 else ""
        except requests.RequestException:
            txt = ""
        # per-SOURCE parse: the embed is a `sources` array (dk, fd, ...). Assign each group id
        # to the nearest preceding shortName so FanDuel groups get tagged, not just DraftKings.
        marks = [(m.start(), 'src', m.group(1))
                 for m in re.finditer(r'shortName\W{0,6}(dk|fd|fanduel|draftkings)', txt, re.I)]
        marks += [(m.start(), 'gid', m.group(1))
                  for m in re.finditer(r"contestGroupId\D{0,6}(\d+)", txt)]
        cur_src, gid_site = 'dk', {}
        for _, kind, val in sorted(marks):
            if kind == 'src':
                cur_src = 'fd' if val.lower().startswith('f') else 'dk'
            elif int(val) > 1000:
                gid_site.setdefault(val, cur_src)
        for g in sorted(gid_site):
            if g not in seen_gids:
                if _record(idx, int(g), d0.isoformat(), d1.isoformat()):
                    idx["groups"][g]["site"] = gid_site[g]
                    n_new += 1
                seen_gids.add(g)
                time.sleep(0.2)
        n_pages += 1
        if n_pages % 14 == 0:
            json.dump(idx, open(INDEX, "w"))
            print(f"  ...{d.isoformat()}: {n_pages} dates walked, {n_new} NFL groups added",
                  file=sys.stderr)
        d += timedelta(days=1)
        time.sleep(0.25)
    json.dump(idx, open(INDEX, "w"))
    print(f"harvest done {d0}..{d1}: +{n_new} groups ({len(idx['groups'])} total indexed)")


# ---------------------------------------------------------------- scan (legacy, 2024+ only)
def scan(gid_lo, gid_hi, target_lo=None, target_hi=None):
    idx = _load_idx()
    done = {int(g) for g in idx.get("_scanned", [])}
    n_new = 0
    for gid in range(gid_lo, gid_hi + 1):
        if gid in done:
            continue
        if _record(idx, gid, target_lo, target_hi):
            n_new += 1
        idx["_scanned"].append(gid)
        if len(idx["_scanned"]) % 100 == 0:
            json.dump(idx, open(INDEX, "w"))
            print(f"  ...scanned {len(idx['_scanned'])} gids, {n_new} NFL groups this run", file=sys.stderr)
        time.sleep(0.15)
    json.dump(idx, open(INDEX, "w"))
    print(f"done scanning {gid_lo}-{gid_hi}: {len(idx['groups'])} NFL groups indexed total")


def scan_dates(d0, d1, pad_hi=150, pad_lo=2800):
    # Early-season contests (Week 1, kickoff) are uploaded in preseason and get group ids
    # well BELOW what the mid-November linear anchor predicts — so pad the low end heavily.
    lo = gid_for(d0) - pad_lo
    hi = gid_for(d1) + pad_hi
    print(f"estimating gid window for {d0}..{d1}: {lo}..{hi} (~{hi-lo} ids)")
    scan(lo, hi, target_lo=d0.isoformat(), target_hi=d1.isoformat())


# ---------------------------------------------------------------- pull ownership
def _players_csv(j, path, date_s, slate, cd):
    players = j.get("players") or {}
    # derive opponent within the slate via shared eventId
    ev = {}
    for p in players.values():
        ev.setdefault(p.get("eventId"), set()).add(p.get("currentTeam"))
    def opp(p):
        teams = ev.get(p.get("eventId"), set())
        others = [t for t in teams if t and t != p.get("currentTeam")]
        return others[0] if others else ""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "slate", "contestId", "contestName", "entryCost", "contestSize",
                    "name", "pos", "team", "opp", "salary", "proj", "ownership", "actual",
                    "homeVisitor", "favDog"])
        for p in players.values():
            w.writerow([date_s, slate, cd["ContestId"], cd["Title"], cd["EntryCost"], cd["ContestSize"],
                        p.get("fullName"), p.get("position"), p.get("currentTeam"), opp(p),
                        p.get("salary"), p.get("projPoints"), p.get("ownership"), p.get("actualPoints"),
                        p.get("homeVisitor"), p.get("favDog")])
    return len(players)


def _stacks_csv(j, path, date_s, cd):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "contestId", "kind", "detail", "ownership_json"])
        for kind in ("teamStacks", "gameStacks"):
            blk = j.get(kind)
            if blk:
                w.writerow([date_s, cd["ContestId"], kind, "", json.dumps(blk)])   # FULL, no cap
    return True


def restacks(want):
    """Re-fetch every indexed contest and write FULL (untruncated) stack tiers into
    stacks_full/*.json (the original pull capped the JSON at 6KB, which cut off the
    top-1% tier). Each file also carries a player id -> (name,pos,team,salary,own) map,
    because the stack combos are id lists and the players CSVs never kept ids. Resumable."""
    if not os.path.exists(INDEX):
        sys.exit("no groups_index.json")
    idx = json.load(open(INDEX))
    sdir = os.path.join(OUT, "stacks_full")
    os.makedirs(sdir, exist_ok=True)
    n = 0
    for gid, g in sorted(idx.get("groups", {}).items(), key=lambda kv: kv[1]["date"]):
        d = g["date"]; ymd = d.replace("-", "")
        for c in g["contests"]:
            cd = {"ContestId": c["id"], "Title": c["title"], "EntryCost": c["cost"],
                  "ContestSize": c["size"]}
            if want != {"all"} and not (set(contest_class(cd)) & want):
                continue
            fp = os.path.join(sdir, f"{d}_{g['slate']}_{c['id']}.json")
            if os.path.exists(fp):
                continue
            j = _get(DATA.format(ymd=ymd, cid=c["id"]))
            if not j or not (j.get("teamStacks") or j.get("gameStacks")):
                continue
            slim = {"date": d, "slate": g["slate"], "contestId": c["id"],
                    "contestName": c["title"], "entryCost": c["cost"],
                    "contestSize": c["size"],
                    "players": {pid: [p.get("fullName"), p.get("position"),
                                      p.get("currentTeam"), p.get("salary"),
                                      p.get("ownership")]
                                for pid, p in (j.get("players") or {}).items()},
                    "teamStacks": j.get("teamStacks"), "gameStacks": j.get("gameStacks")}
            with open(fp, "w", encoding="utf-8") as fh:
                json.dump(slim, fh)
            n += 1
            if n % 50 == 0:
                print(f"  ...{n} contests re-stacked (at {d})", flush=True)
            time.sleep(0.3)
    print(f"done: {n} full stacks files -> {sdir}")


def _hunt_user(obj, target, path="", depth=0):
    """Recursively find records containing the target username (case-insensitive). Returns
    [(path, record)] where record is the smallest dict containing the match. Shape-agnostic —
    FL's `users` blob layout is unverified, so we keep whatever surrounds the hit."""
    hits = []
    if depth > 6:
        return hits
    if isinstance(obj, dict):
        matched = any(isinstance(v, str) and v.lower() == target for v in obj.values())
        if matched:
            hits.append((path, obj))
        else:
            for k, v in obj.items():
                if isinstance(k, str) and k.lower() == target:
                    hits.append((path + "/" + k, v if isinstance(v, dict) else {"value": v}))
                hits += _hunt_user(v, target, path + "/" + str(k), depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += _hunt_user(v, target, path + f"[{i}]", depth + 1)
    return hits


def winners(want, user=None):
    """Pull WINNING-LINEUP composition: the data endpoint's `exposures` block gives player
    exposure among the top finishers, keyed by tier (1/10/20/100 = top-N% of the field; tier 1
    ~= the winner(s)). Writes winners/{date}_{slate}_{cid}.csv (one row per tier x player) plus
    contest_meta.csv (duplicateLineups, uniqueLineups, cashLine, totalPrizes — sim calibration).
    Resumable: skips contests whose winners file exists."""
    if not os.path.exists(INDEX):
        sys.exit("no groups_index.json — run --harvest-dates first.")
    idx = json.load(open(INDEX))
    wdir = os.path.join(OUT, "winners")
    os.makedirs(wdir, exist_ok=True)
    udir = os.path.join(OUT, "users")
    if user:
        os.makedirs(udir, exist_ok=True)
        user = user.lower()
        u_summary = open(os.path.join(udir, f"_{user}_index.csv"), "a", newline="", encoding="utf-8")
        usw = csv.writer(u_summary)
        if u_summary.tell() == 0:
            usw.writerow(["date", "slate", "contestId", "contestName", "hits", "file"])
    meta_path = os.path.join(OUT, "contest_meta.csv")
    have_meta = set()
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            have_meta = {r["contestId"] for r in csv.DictReader(f)}
    mf = open(meta_path, "a", newline="", encoding="utf-8")
    mw = csv.writer(mf)
    if not have_meta:
        mw.writerow(["date", "slate", "contestId", "contestName", "entryCost", "contestSize",
                     "cashLine", "duplicateLineups", "uniqueLineups", "totalPrizes"])
    n_files = 0
    for gid, g in sorted(idx.get("groups", {}).items(), key=lambda kv: kv[1]["date"]):
        d = g["date"]; ymd = d.replace("-", "")
        for c in g["contests"]:
            cd = {"ContestId": c["id"], "Title": c["title"], "EntryCost": c["cost"],
                  "ContestSize": c["size"]}
            if want != {"all"} and not (set(contest_class(cd)) & want):
                continue
            fp = os.path.join(wdir, f"{d}_{g['slate']}_{c['id']}.csv")
            ufp = os.path.join(udir, f"{d}_{c['id']}_{user}.json") if user else None
            if os.path.exists(fp) and (not user or os.path.exists(ufp + ".done")):
                continue
            j = _get(DATA.format(ymd=ymd, cid=c["id"]))
            if not j:
                continue
            if user:
                hits = _hunt_user(j.get("users"), user)
                if hits:
                    json.dump({"date": d, "contest": c["title"], "hits":
                               [{"path": p, "record": r} for p, r in hits[:50]]},
                              open(ufp, "w"), indent=1)
                    usw.writerow([d, g["slate"], c["id"], c["title"][:40], len(hits),
                                  os.path.basename(ufp)])
                    print(f"  ** {user} FOUND in {c['title'][:36]} ({d}) — {len(hits)} hit(s)")
                open(ufp + ".done", "w").write("1")   # scanned marker (even when no hits)
            players = j.get("players") or {}
            cm = j.get("contest") or {}
            if str(c["id"]) not in have_meta:
                mw.writerow([d, g["slate"], c["id"], cm.get("contestName", c["title"]),
                             cm.get("entryCost", c["cost"]), cm.get("contestSize", c["size"]),
                             cm.get("cashLine"), cm.get("duplicateLineups"),
                             cm.get("uniqueLineups"), cm.get("totalPrizes")])
                have_meta.add(str(c["id"]))
            exp = j.get("exposures") or {}
            if not exp or os.path.exists(fp):
                continue
            with open(fp, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["date", "slate", "contestId", "tier_top_pct", "player", "pos", "team",
                            "salary", "field_ownership", "top_ct", "top_pct"])
                for tier, blk in sorted(exp.items(), key=lambda kv: int(kv[0])):
                    for pk, e in (blk.get("exposureCounts") or {}).items():
                        p = players.get(pk) or {}
                        w.writerow([d, g["slate"], c["id"], tier, p.get("fullName", pk),
                                    p.get("position"), p.get("currentTeam"), p.get("salary"),
                                    p.get("ownership"), e.get("exposureCt"), e.get("exposurePerc")])
            n_files += 1
            print(f"  {d} {g['slate']:9} {c['id']} '{c['title'][:30]}'  tiers={sorted(exp.keys())}")
            time.sleep(0.3)
    mf.close()
    if user:
        u_summary.close()
        print(f"user scan '{user}': see {udir}/_{user}_index.csv for every contest hit")
    print(f"done: {n_files} winners files -> {wdir}; meta -> contest_meta.csv")


def pull(want, with_stacks):
    if not os.path.exists(INDEX):
        sys.exit("no groups_index.json — run --scan-dates first.")
    idx = json.load(open(INDEX))
    groups = idx.get("groups", {})
    pdir = os.path.join(OUT, "players"); sdir = os.path.join(OUT, "stacks")
    n_files = 0
    for gid, g in sorted(groups.items(), key=lambda kv: kv[1]["date"]):
        d = g["date"]; ymd = d.replace("-", "")
        for c in g["contests"]:
            cd = {"ContestId": c["id"], "Title": c["title"], "EntryCost": c["cost"],
                  "ContestSize": c["size"]}
            tags = set(contest_class(cd))
            if want != {"all"} and not (tags & want):
                continue
            slate = g["slate"]
            fp = os.path.join(pdir, f"{d}_{slate}_{c['id']}.csv")
            if os.path.exists(fp):
                continue
            j = _get(DATA.format(ymd=ymd, cid=c["id"]))
            if not j or not j.get("players"):
                continue
            n = _players_csv(j, fp, d, slate, cd)
            if with_stacks:
                _stacks_csv(j, os.path.join(sdir, f"{d}_{slate}_{c['id']}.csv"), d, cd)
            n_files += 1
            print(f"  {d} {slate:9} {c['id']} '{c['title'][:32]}'  {n} players"
                  + ("  +stacks" if with_stacks else ""))
            time.sleep(0.3)
    print(f"done: wrote {n_files} contest files to {pdir}")


# ---------------------------------------------------------------- discover / validate
def discover():
    print("validating parse on a known NFL main slate (gid 115396, 2024-11-17)...")
    j = _get(GROUP.format(gid=115396))
    if not j:
        sys.exit("could not fetch group 115396 — check network.")
    print(f"  group has {len(j)} contests; classes seen:")
    for c in j:
        cd = c["ContestData"]
        print(f"    {cd['ContestId']}  ${cd['EntryCost']:<5} size {cd['ContestSize']:>7}  "
              f"{contest_class(cd)}  '{cd['Title'][:40]}'")
    milly = next((c["ContestData"] for c in j if "milly" in contest_class(c["ContestData"])), None)
    if milly:
        d = _get(DATA.format(ymd="20241117", cid=milly["ContestId"]))
        ps = list((d or {}).get("players", {}).values())
        withown = [p for p in ps if p.get("ownership")]
        top = sorted(withown, key=lambda p: -p["ownership"])[:5]
        print(f"\n  Milly ownership sample ({milly['ContestId']}): {len(ps)} players, "
              f"{len(withown)} owned")
        for p in top:
            print(f"    {p['fullName']:22} {p['currentTeam']:3} own {p['ownership']:5}%  "
                  f"proj {p['projPoints']}  actual {p['actualPoints']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--harvest-dates", nargs=2, metavar=("START", "END"),
                    help="RECOMMENDED: resolve each date's groups from the app page (works 2021+, ~1 min/season)")
    ap.add_argument("--scan", nargs=2, type=int, metavar=("LO", "HI"), help="scan a raw gid range")
    ap.add_argument("--scan-dates", nargs=2, metavar=("START", "END"), help="legacy id-scan (dense 2024+ era only)")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--winners", action="store_true",
                    help="pull top-finisher exposure tiers (winning-lineup composition) + contest meta")
    ap.add_argument("--user", help="also extract this username's entries from each contest's users blob "
                                   "(e.g. --user rsbathla); writes data/fantasylabs/users/")
    ap.add_argument("--all-types", action="store_true", help="pull every NFL contest")
    ap.add_argument("--milly", action="store_true")
    ap.add_argument("--highroller", action="store_true", help="$4,444 contests")
    ap.add_argument("--wildcat", action="store_true", help="$333 Wildcat")
    ap.add_argument("--showdown", action="store_true")
    ap.add_argument("--stacks", action="store_true", help="also dump team/game stack ownership")
    ap.add_argument("--restacks", action="store_true",
                    help="re-fetch FULL (untruncated) stack tiers into stacks_full/")
    a = ap.parse_args()

    if a.discover:
        discover(); return 0
    if a.harvest_dates:
        harvest_dates(date.fromisoformat(a.harvest_dates[0]),
                      date.fromisoformat(a.harvest_dates[1])); return 0
    if a.scan:
        scan(a.scan[0], a.scan[1]); return 0
    if a.scan_dates:
        scan_dates(date.fromisoformat(a.scan_dates[0]), date.fromisoformat(a.scan_dates[1])); return 0
    if a.restacks:
        want = {"all"} if a.all_types else set()
        for k in ("milly", "highroller", "wildcat", "showdown"):
            if getattr(a, k):
                want.add(k)
        restacks(want or {"all"}); return 0
    if a.pull or a.winners:
        want = {"all"} if a.all_types else set()
        for k in ("milly", "highroller", "wildcat", "showdown"):
            if getattr(a, k):
                want.add(k)
        if not want:
            sys.exit("choose contests: --all-types or one of --milly/--highroller/--wildcat/--showdown")
        if a.pull:
            pull(want, a.stacks)
        if a.winners or a.user:
            winners(want, user=a.user)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    main()
