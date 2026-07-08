#!/usr/bin/env python3
"""fc_puller.py — FantasyCruncher "Lineup Rewind" historical pull (salary + ownership + results).

WHY: the repo has best-ball ADP but no DFS salary/ownership. FantasyCruncher's Lineup Rewind carries,
per player per weekly slate, for DK and FD: Salary, Actual fantasy score, Actual Ownership % (your
Milly-Maker contests), Projected Ownership, FC projection, Value — back to 2015. This pulls every
week into data/fantasycruncher/{site}/{period}.csv so we can build salary-weighted bring-back
correlation, ownership leverage, and a real DFS backtest.

SEED-AND-ITERATE (same pattern as fp_puller.py):
  1. In the FantasyCruncher tab, open DevTools -> Network, reload a Lineup Rewind page
     (e.g. /lineup-rewind/draftkings/NFL/2025-week-18), click the DOCUMENT request (the .../2025-week-18
     one, type "document"), right-click -> Copy -> "Copy as cURL", paste it into fc_seed.sh, save.
  2. python3 fc_puller.py --discover        # prints the embedded data shape from ONE page (verify parser)
  3. python3 fc_puller.py --all             # loops every period -> CSVs (resumes; skips done weeks)
     python3 fc_puller.py --seasons 2023-2025 --site draftkings
     python3 fc_puller.py --period 2025-week-18            # one week

SECURITY: fc_seed.sh holds your logged-in session cookie. It is git-ignored, never printed by this
script, and only sent back to fantasycruncher.com. Log out / re-login to rotate it when you're done.
No password is ever handled here.
"""
import argparse, csv, html as _html, json, os, re, sys, time, urllib.parse

SEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fc_seed.sh")
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fantasycruncher")

try:
    import requests
except ImportError:
    sys.exit("need requests: pip install requests --break-system-packages")


# ----------------------------------------------------------------- seed / session
def parse_curl(path):
    """Extract (base_headers, cookies) from a pasted 'Copy as cURL'. Never logs the values."""
    if not os.path.exists(path):
        sys.exit(f"missing {path} — paste a 'Copy as cURL' of a Lineup Rewind page there (see header).")
    txt = open(path, encoding="utf-8").read().replace("\\\n", " ")
    headers, cookies = {}, ""
    for m in re.finditer(r"-H\s+'([^']+)'", txt):
        k, _, v = m.group(1).partition(":")
        k, v = k.strip(), v.strip()
        if k.lower() == "cookie":
            cookies = v
        elif k.lower() not in ("content-length", "accept-encoding"):
            headers[k] = v
    for m in re.finditer(r"(?:-b|--cookie)\s+'([^']+)'", txt):
        cookies = m.group(1)
    if not cookies:
        sys.exit("no Cookie found in fc_seed.sh — re-copy the cURL of the DOCUMENT (page) request while logged in.")
    headers.setdefault("User-Agent", "Mozilla/5.0")
    return headers, cookies


def make_session():
    headers, cookies = parse_curl(SEED)
    s = requests.Session()
    s.headers.update(headers)
    s.headers["Cookie"] = cookies
    return s


def get(s, url):
    for attempt in range(4):
        try:
            r = s.get(url, timeout=45)
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            if r.status_code in (401, 403):
                sys.exit(f"auth failed ({r.status_code}) — session cookie expired; re-copy fc_seed.sh while logged in.")
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    return None


# ----------------------------------------------------------------- period enumeration
def get_periods(s, site):
    url = f"https://www.fantasycruncher.com/ajax/getLeaguePeriods.php?league=NFL&site={site}"
    txt = get(s, url) or ""
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        sys.exit("could not read period list — check the cookie/site.")
    periods = json.loads(m.group(0))
    # newest-first in the file; return sorted oldest->newest as (year, week, key)
    out = []
    for k in periods:
        mm = re.match(r"(\d{4})-week-(\d+)", k)
        if mm:
            out.append((int(mm.group(1)), int(mm.group(2)), k))
    return sorted(out)


# ----------------------------------------------------------------- embedded-data extraction
PLAYER_KEY_HINTS = ("Salary", "salary", "Actual", "ActOwn", "Player Name", "player_name", "pname")


def _json_blobs(page):
    """Yield every top-level {..}/[..] literal >2KB found in inline <script> blocks (brace-matched)."""
    for sm in re.finditer(r"<script[^>]*>(.*?)</script>", page, re.S):
        body = sm.group(1)
        i = 0
        while i < len(body):
            c = body[i]
            if c in "[{":
                depth, j, instr, esc, q = 0, i, False, False, ""
                while j < len(body):
                    cj = body[j]
                    if instr:
                        if esc:
                            esc = False
                        elif cj == "\\":
                            esc = True
                        elif cj == q:
                            instr = False
                    else:
                        if cj in "\"'":
                            instr, q = True, cj
                        elif cj in "[{":
                            depth += 1
                        elif cj in "]}":
                            depth -= 1
                            if depth == 0:
                                break
                    j += 1
                blob = body[i:j + 1]
                if len(blob) > 2048:
                    yield blob
                    i = j + 1
                    continue
            i += 1


def _rows_from(blob):
    try:
        obj = json.loads(blob)
    except Exception:
        return None
    rows = obj if isinstance(obj, list) else (list(obj.values()) if isinstance(obj, dict) else None)
    if not rows or not isinstance(rows[0], dict):
        return None
    keys = set(rows[0].keys())
    if sum(1 for h in PLAYER_KEY_HINTS if h in keys) >= 1 and len(keys) >= 8:
        return rows
    return None


def extract_players(page):
    """Return the player-row list from a rewind page, or [] if not found."""
    best = []
    for blob in _json_blobs(page):
        rows = _rows_from(blob)
        if rows and len(rows) > len(best):
            best = rows
    return best


def discover(page):
    print(f"page bytes: {len(page)}")
    n = 0
    for blob in _json_blobs(page):
        try:
            obj = json.loads(blob)
        except Exception:
            continue
        rows = obj if isinstance(obj, list) else (list(obj.values()) if isinstance(obj, dict) else [])
        if rows and isinstance(rows[0], dict):
            n += 1
            keys = list(rows[0].keys())
            hit = [h for h in PLAYER_KEY_HINTS if h in rows[0]]
            print(f"\n[candidate {n}] rows={len(rows)} keys={len(keys)} player_hints={hit}")
            print("  keys:", ", ".join(map(str, keys)))
            if hit:   # the player table — show every key mapped to its sample value
                print("  row0 full:", json.dumps({k: rows[0][k] for k in keys}, default=str)[:1200])
    if not n:
        print("no JSON row-blobs found — paste me the output of: "
              "document.querySelectorAll('script').length, and one script's first 400 chars.")


# ---------------- game/team Vegas blob: team totals, game total, proj plays, final scores --------
_TEAM_HINTS = ("implied_pts", "opp_implied_pts", "proj_plays")       # per-team rows (discover cand. 4)
_ODDS_HINTS = ("total", "finalscore_HomeTeam", "home_implied_pts")   # per-game rows (discover cand. 3)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pick_blob(page, hints, minrows):
    best = []
    for blob in _json_blobs(page):
        try:
            obj = json.loads(blob)
        except Exception:
            continue
        rows = obj if isinstance(obj, list) else (list(obj.values()) if isinstance(obj, dict) else [])
        if rows and isinstance(rows[0], dict) and sum(1 for h in hints if h in rows[0]) >= 2 and len(rows) >= minrows:
            if len(rows) > len(best):
                best = rows
    return best


def extract_games(page):
    """per-TEAM rows: team implied total, opp total, game total, spread, proj plays/att, final scores."""
    teams = _pick_blob(page, _TEAM_HINTS, 2)
    odds = {str(g.get("GameId")): g for g in _pick_blob(page, _ODDS_HINTS, 1)}
    out = []
    for t in teams:
        g = odds.get(str(t.get("GameId")), {})
        imp, opp = _num(t.get("implied_pts")), _num(t.get("opp_implied_pts"))
        row = {"GameId": str(t.get("GameId")), "Team": t.get("Team"), "is_home": t.get("is_home"),
               "team_total": imp, "opp_total": opp,
               "game_total": (imp + opp) if (imp is not None and opp is not None) else _num(g.get("total")),
               "spread": _num(t.get("spread")), "proj_plays": _num(t.get("proj_plays")),
               "proj_pass_att": _num(t.get("proj_passing_att")), "proj_rush_att": _num(t.get("proj_rushing_att"))}
        if t.get("Team") == g.get("HomeTeam"):
            row["final_score"], row["opp_final"] = _num(g.get("finalscore_HomeTeam")), _num(g.get("finalscore_AwayTeam"))
        elif t.get("Team") == g.get("AwayTeam"):
            row["final_score"], row["opp_final"] = _num(g.get("finalscore_AwayTeam")), _num(g.get("finalscore_HomeTeam"))
        out.append(row)
    return out


def games_to_csv(rows, period, site, path):
    cols = ["GameId", "Team", "is_home", "team_total", "opp_total", "game_total", "spread",
            "proj_plays", "proj_pass_att", "proj_rush_att", "final_score", "opp_final"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["period", "site"] + cols)
        for r in rows:
            w.writerow([period, site] + [r.get(c, "") for c in cols])
    return len(rows)


# ----------------------------------------------------------------- CSV writing
# the analytically useful columns, floated to the front (raw FC keys, from --discover); every OTHER
# key is still written after these, so nothing (incl. whatever ownership is named) is ever dropped.
PRIORITY = ["PlayerName", "PlayerPos", "pDepth", "Team", "opp", "GameId", "AwayTeam", "HomeTeam",
            "Salary", "Last_Sal", "Actual_Pts", "Proj_Score", "Default_Proj_Score",
            "proj_tgt_share", "proj_rush_share",
            "trueValue", "value", "Avg_Pts", "stddev", "consistency", "lastYearAvg", "thisYearAvg",
            "Injury_status", "Status", "StatusDetails", "DateTime", "Period"]
# drop only empty/redundant fields; KEEP misc_data (proj target share), proj_stats (proj stat line),
# stat_avgs (last-season stats), slate_data (per-slate salaries) as JSON columns — all analytically useful.
DROP = {"Stat_cats", "depth", "rotoworld_URL"}


def _flat(rows):
    """pull the two most useful nested values up to flat columns for convenience (kept alongside JSON)."""
    for r in rows:
        md = r.get("misc_data")
        if isinstance(md, dict):
            r["proj_tgt_share"] = md.get("proj_share", {}).get("pct_receiving_tar", "")
            r["proj_rush_share"] = md.get("proj_share", {}).get("pct_rushing_att", "")


def _opp(r):
    t, a, h = r.get("Team"), r.get("AwayTeam"), r.get("HomeTeam")
    return (h if t == a else a if t == h else "") if (t and a and h) else ""


def _cell(v):
    if isinstance(v, (dict, list)):
        try: return json.dumps(v, separators=(",", ":"))[:2000]
        except Exception: return ""
    return _html.unescape(re.sub("<[^>]+>", "", v)).strip() if isinstance(v, str) else v


def rows_to_csv(rows, period, site, path):
    _flat(rows)
    for r in rows:
        r["opp"] = _opp(r)
    allkeys = []
    for r in rows[:8]:
        for k in r:
            if k not in allkeys and k not in DROP:
                allkeys.append(k)
    ordered = [k for k in PRIORITY if k in allkeys] + [k for k in allkeys if k not in PRIORITY]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["period", "site"] + ordered)
        for r in rows:
            w.writerow([period, site] + [_cell(r.get(k, "")) for k in ordered])
    return len(rows), len(ordered)


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="draftkings", choices=["draftkings", "fanduel"])
    ap.add_argument("--all", action="store_true", help="pull every available period")
    ap.add_argument("--seasons", help="year range, e.g. 2023-2025")
    ap.add_argument("--period", help="single period, e.g. 2025-week-18")
    ap.add_argument("--discover", action="store_true", help="dump one page's data shape and exit")
    ap.add_argument("--inspect", help="dump ONE player's full raw record from a page (find where ownership lives)")
    ap.add_argument("--games", action="store_true", help="pull per-team Vegas (team total, game total, proj plays, final scores) per week")
    ap.add_argument("--sleep", type=float, default=1.5)
    a = ap.parse_args()
    s = make_session()

    if a.discover:
        per = a.period or "2025-week-18"
        page = get(s, f"https://www.fantasycruncher.com/lineup-rewind/{a.site}/NFL/{per}")
        if not page:
            sys.exit("could not fetch the page — check fc_seed.sh cookie.")
        discover(page)
        return 0

    if a.inspect:
        per = a.period or "2025-week-18"
        page = get(s, f"https://www.fantasycruncher.com/lineup-rewind/{a.site}/NFL/{per}")
        rows = extract_players(page) if page else []
        match = [r for r in rows if a.inspect.lower() in str(r.get("PlayerName", "")).lower()]
        if not match:
            print("no match; sample names:", [r.get("PlayerName") for r in rows[:6]])
            return 0
        r = match[0]
        print(f"=== full raw record: {r.get('PlayerName')} ({per}) — {len(r)} fields ===")
        for k in sorted(r):
            v = r[k]
            v = json.dumps(v)[:400] if isinstance(v, (dict, list)) else v
            print(f"  {k}: {v}")
        return 0

    if a.period:
        targets = [a.period]
    else:
        periods = get_periods(s, a.site)
        if a.seasons:
            lo, hi = (int(x) for x in a.seasons.split("-"))
            periods = [p for p in periods if lo <= p[0] <= hi]
        elif not (a.all or a.games):
            sys.exit("pass --all, --games, --seasons YYYY-YYYY, or --period YYYY-week-N")
        targets = [p[2] for p in periods]

    if a.games:
        gdir = os.path.join(OUTDIR, a.site + "_games")
        print(f"[fc_puller] GAMES: {len(targets)} periods · -> {gdir}/")
        gp = gempty = 0
        for per in targets:
            path = os.path.join(gdir, f"{per}.csv")
            if os.path.exists(path) and os.path.getsize(path) > 100:
                continue
            page = get(s, f"https://www.fantasycruncher.com/lineup-rewind/{a.site}/NFL/{per}")
            rows = extract_games(page) if page else []
            if not rows:
                gempty += 1
                print(f"  {per}: no game rows")
                continue
            n = games_to_csv(rows, per, a.site, path)
            gp += 1
            print(f"  {per}: {n} teams -> {os.path.relpath(path)}")
            time.sleep(a.sleep)
        print(f"[fc_puller] games done. pulled {gp}, empty {gempty}.")
        return 0

    print(f"[fc_puller] {len(targets)} periods · site={a.site} · -> {OUTDIR}/{a.site}/")
    done = pulled = empty = 0
    for per in targets:
        path = os.path.join(OUTDIR, a.site, f"{per}.csv")
        if os.path.exists(path) and os.path.getsize(path) > 200:
            done += 1
            continue
        page = get(s, f"https://www.fantasycruncher.com/lineup-rewind/{a.site}/NFL/{per}")
        rows = extract_players(page) if page else []
        if not rows:
            empty += 1
            print(f"  {per}: no rows (locked/empty slate or parser miss)")
            continue
        n, c = rows_to_csv(rows, per, a.site, path)
        pulled += 1
        print(f"  {per}: {n} players, {c} cols -> {os.path.relpath(path)}")
        time.sleep(a.sleep)
    print(f"[fc_puller] done. pulled {pulled}, already-had {done}, empty {empty}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
