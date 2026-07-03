#!/usr/bin/env python3
"""ask_data.py — grounded data librarian for the repo.

Resolves a player or team across EVERY analytical layer and prints values WITH provenance
(file - year), so any answer traces to a source and its vintage. Handles the four player-key
conventions (fn-normalized, raw display, nflverse abbrev, SIS nickname) and the year-vintage
traps (2025-only charting vs 2yr-pooled vs 2026-projection).

  python3 ask_data.py player "Ja'Marr Chase"     full footprint across all layers
  python3 ask_data.py team TB                     defense shell freq + splits + offense + PROE
  python3 ask_data.py coverage "Ja'Marr Chase"    per-scheme YPRR (Cover 0/1/2/3/4/6), best->worst
  python3 ask_data.py matchup "Ja'Marr Chase" TB  his coverage strengths vs the opp's shell mix

Catalog of layers + year semantics: DATA_CATALOG.md.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    import core
    fn = core.fn
except Exception:
    import re
    def fn(s):
        s = re.sub(r"[^a-z ]", "", str(s).lower())
        s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
        return re.sub(r"\s+", " ", s).strip()


def J(p):
    fp = os.path.join(HERE, p)
    return json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else None


def csv_rows(p):
    fp = os.path.join(HERE, p)
    if not os.path.exists(fp):
        return []
    import csv
    return list(csv.DictReader(open(fp, encoding="utf-8")))


def line(label, val, src, year):
    if val is None or val == "":
        return
    print(f"  {label:26s} {str(val):>10s}   [{src} · {year}]")


# ---------------------------------------------------------------- resolvers
def find_fn(d, name, sub=None):
    """Look up an fn-keyed dict (optionally under a sub-key like 'players'/'teams')."""
    if d is None:
        return None
    root = d.get(sub, d) if sub else d
    return root.get(fn(name))


def find_raw(d, name):
    """Look up a raw-display-name-keyed dict via fn-match on keys or .name."""
    if d is None:
        return None
    target = fn(name)
    for k, v in d.items():
        if fn(k) == target or (isinstance(v, dict) and fn(v.get("name", "")) == target):
            return v
    return None


# ---------------------------------------------------------------- player
def player(name):
    print(f"\n=== {name}  —  data footprint (value  [source · year]) ===\n")

    ch = find_fn(J("boom/chart2yr.json"), name)
    if ch:
        print("Charting — receiving efficiency (chart2yr.json, per-season):")
        for yr in ("y2024", "y2025"):
            b = ch.get(yr) or {}
            if b:
                line(f"YPRR ({yr[1:]})", b.get("yprr"), "chart2yr", yr[1:])
                line(f"aDOT ({yr[1:]})", b.get("aDOT"), "chart2yr", yr[1:])
                line(f"air-yards share % ({yr[1:]})", b.get("ay_share"), "chart2yr", yr[1:])
                line(f"RZ tgt rate % ({yr[1:]})", b.get("rz_tgt_rate"), "chart2yr", yr[1:])
                line(f"slot % ({yr[1:]})", b.get("slot_pct"), "chart2yr", yr[1:])

    cs = find_fn(J("boom/coverage_split.json"), name)
    if cs:
        print("\nMan vs zone — YPRR (coverage_split.json, 2024+2025 POOLED):")
        line("YPRR vs man", cs.get("man_yprr"), "coverage_split", "2yr")
        line("YPRR vs zone", cs.get("zone_yprr"), "coverage_split", "2yr")
        line("man-zone delta", cs.get("delta"), "coverage_split", "2yr")

    mz = find_raw(J("boom/manzone_2yr.json"), name)
    if mz:
        print("\nMan vs zone — PER-YEAR split (manzone_2yr.json; raw-name keyed):")
        line("man YPRR (2yr blend)", mz.get("man2y"), "manzone_2yr", "2yr")
        line("man-zone delta 2024", mz.get("d24"), "manzone_2yr", "2024")
        line("man-zone delta 2025", mz.get("d25"), "manzone_2yr", "2025")
        line("read", mz.get("read"), "manzone_2yr", "2yr")

    pr = find_raw(J("profiles/player_profiles.json"), name)
    if pr:
        sit = pr.get("situations") or {}
        m = sit.get("rec_vs_man") or {}
        z = sit.get("rec_vs_zone") or {}
        if m or z:
            print("\nMan vs zone — profiles/player_profiles.json (2025 ONLY; raw-name keyed):")
            line("YPRR vs man (val)", m.get("val"), "player_profiles", "2025")
            line("  vs man (pctl)", m.get("pct"), "player_profiles", "2025")
            line("YPRR vs zone (val)", z.get("val"), "player_profiles", "2025")
            line("  vs zone (pctl)", z.get("pct"), "player_profiles", "2025")

    cc = find_fn(J("cc_context.json"), name)
    if cc:
        sp = cc.get("splits") or {}
        if sp:
            print("\nCommand-center splits (cc_context.json, 2025 ONLY):")
            line("YPRR vs man (2025)", sp.get("yprr_man"), "cc_context", "2025")
            line("YPRR vs zone (2025)", sp.get("yprr_zone"), "cc_context", "2025")
            line("man route share %", sp.get("man_route_sh"), "cc_context", "2025")

    rz = find_fn(J("boom/redzone.json"), name)
    if rz:
        print("\nRed zone (redzone.json, 2024+2025 pooled):")
        line("RZ tgt share %", rz.get("rz_tgt_share"), "redzone", "2yr")
        line("end-zone TD/game", rz.get("ez_td_pg"), "redzone", "2yr")

    rze = find_fn(J("rz_equity_2026.json"), name, sub="teams")
    if rze:
        line("RZ role z (pos-centered)", rze.get("rz_role_z"), "rz_equity_2026", "2yr->2026")

    mo = find_fn(J("boom/motion.json"), name)
    if mo:
        print("\nMotion (motion.json, 2yr):")
        line("motion %", mo.get("motion_pct"), "motion", "2yr")
        line("YPRR lift w/ motion", mo.get("motion_lift"), "motion", "2yr")

    fr = find_fn(J("flag_ranks.json"), name, sub="players")
    if fr:
        print("\nRanking / flags (flag_ranks.json, 2026 projection):")
        line("ceiling pctl", fr.get("ceil_pctl"), "flag_ranks", "2026")
        line("target share %", fr.get("tgt_sh"), "flag_ranks", "2026")
        tf = fr.get("top_flags")
        if tf:
            print(f"  {'top flags':26s}   {', '.join(tf[:4])}   [flag_ranks · 2026]")

    sis_m = [r for r in csv_rows("sis_value/receiving_man.csv") if fn(r.get("Player", "")) == fn(name)]
    sis_z = [r for r in csv_rows("sis_value/receiving_zone.csv") if fn(r.get("Player", "")) == fn(name)]
    if sis_m or sis_z:
        print("\nSIS value split (sis_value/*, 2025 ONLY):")
        if sis_m:
            line("value/route vs man", sis_m[0].get("PE Per Route"), "receiving_man", "2025")
        if sis_z:
            line("value/route vs zone", sis_z[0].get("PE Per Route"), "receiving_zone", "2025")

    coverage(name, header=False)


# ---------------------------------------------------------------- coverage (per-scheme)
def coverage(name, header=True):
    spec = J("boom/coverage_route_spec.json")
    if not spec:
        return
    players = spec.get("players", spec)
    rec = None
    if isinstance(players, dict):
        rec = players.get(fn(name)) or find_raw(players, name)
    elif isinstance(players, list):
        for p in players:
            if fn(p.get("key", p.get("name", ""))) == fn(name):
                rec = p; break
    schemes = (rec or {}).get("schemes") if rec else None
    if not schemes:
        return
    print("\nPer-SCHEME YPRR (coverage_route_spec.json, 2024+2025 pooled; best->worst):")
    order = sorted(schemes.items(), key=lambda kv: -(kv[1].get("pctl") or 0))
    for sc, v in order:
        q = "" if v.get("q", True) else "  (thin sample)"
        print(f"  {sc:14s} YPRR {v.get('yprr'):>6}  pctl {str(v.get('pctl')):>4}  ({v.get('rte')} rte){q}")


# ---------------------------------------------------------------- team
LEAGUE_C3 = None
def team(abbr):
    abbr = abbr.upper()
    print(f"\n=== {abbr}  —  team data (value  [source · year]) ===\n")

    sh = J("boom/defense_shell.json")
    if sh and abbr in sh:
        t = sh[abbr]; lg = sh.get("_LEAGUE", {})
        print("Defensive coverage shell — % of dropbacks (defense_shell.json, 2025):")
        for k, lab in [("man", "man"), ("c2", "Cover 2"), ("c3", "Cover 3"), ("c4", "Cover 4"),
                       ("c6", "Cover 6"), ("single_high", "single-high"), ("two_high", "two-high")]:
            v = t.get(k)
            if v is None:
                continue
            la = lg.get(k)
            # rank among 32 for this shell
            rk = ""
            vals = sorted([tt.get(k) for kk, tt in sh.items() if kk != "_LEAGUE" and tt.get(k) is not None], reverse=True)
            if t.get(k) in vals:
                rk = f"  (#{vals.index(t.get(k))+1}/32)"
            avg = f"  vs lg {la:.1f}" if isinstance(la, (int, float)) else ""
            print(f"  {lab:14s} {v:>6}%{avg}{rk}")

    ds = J("defense_splits.json")
    if ds and abbr in ds:
        t = ds[abbr]
        print("\nCoverage softness allowed (defense_splits.json, 2025 primary):")
        for ax in ("vs_man", "vs_zone", "deep"):
            b = t.get(ax) or {}
            line(f"{ax} softness pctl", b.get("softness_pctl"), "defense_splits", "2025")
        u = t.get("units") or {}
        line("pass-cov pctl (low=soft)", u.get("pass_cov_pctl"), "defense_splits", "2025")

    op = J("offense_profile.json")
    ot = (op or {}).get("teams", op or {}).get(abbr) if op else None
    if ot:
        print("\nOffense identity (offense_profile.json, 2025 base + 2026 outlook):")
        pace = ot.get("pace") or {}
        line("plays/game", pace.get("plays_pg"), "offense_profile", "2025")
        line("pass rate %", ot.get("pass_rate"), "offense_profile", "2025")
        line("playcaller (2026)", ot.get("playcaller"), "offense_profile", "2026")

    pt = J("proe_tendency_2026.json")
    ptt = (pt or {}).get("teams", {}).get(abbr) if pt else None
    if ptt:
        print("\nPROE pass tendency (proe_tendency_2026.json):")
        line("PROE 2025 (actual)", ptt.get("proe_2025"), "proe_tendency", "2025")
        line("PROE 2026 (w/ carousel)", ptt.get("proe_2026"), "proe_tendency", "2026*")

    tc = J("team_ceiling.json")
    tct = (tc or {}).get("teams", {}).get(abbr) if tc else None
    if tct:
        line("season-ceiling tier", tct.get("tier"), "team_ceiling", "2026")


# ---------------------------------------------------------------- matchup
def matchup(name, abbr):
    abbr = abbr.upper()
    print(f"\n=== {name}  vs  {abbr}  —  coverage-scheme fit ===\n")
    spec = J("boom/coverage_route_spec.json")
    sh = J("boom/defense_shell.json")
    if not spec or not sh or abbr not in sh:
        print("  (missing coverage_route_spec.json or defense_shell.json)")
        return
    players = spec.get("players", spec)
    rec = players.get(fn(name)) if isinstance(players, dict) else None
    if rec is None and isinstance(players, dict):
        rec = find_raw(players, name)
    if rec is None and isinstance(players, list):
        rec = next((p for p in players if fn(p.get("key", p.get("name", ""))) == fn(name)), None)
    schemes = (rec or {}).get("schemes") or {}
    tsh, lg = sh[abbr], sh.get("_LEAGUE", {})
    shell_key = {"Cover 0": "man", "Cover 1": "man", "Man Cover 2": "man",
                 "Cover 2": "c2", "Cover 3": "c3", "Cover 4": "c4", "Cover 6": "c6"}
    print(f"{'coverage':14s} {'his YPRR/pctl':>16s} {abbr+' freq':>10s} {'lg avg':>8s}  read")
    rows = []
    for sc, v in schemes.items():
        k = shell_key.get(sc)
        freq = tsh.get(k) if k else None
        rows.append((v.get("pctl") or 0, sc, v, freq, lg.get(k)))
    for pctl, sc, v, freq, la in sorted(rows, key=lambda r: -(r[3] or 0)):
        if freq is None:
            continue
        strong = (v.get("pctl") or 0) >= 70
        heavy = la is not None and freq >= la
        read = ("EDGE — he crushes it & they play it a lot" if strong and heavy
                else "he's strong here but they play it less" if strong
                else "they play it a lot but he's ordinary" if heavy else "neutral")
        avg = f"{la:.0f}%" if isinstance(la, (int, float)) else "—"
        print(f"  {sc:14s} {str(v.get('yprr'))+' / '+str(v.get('pctl')):>16s} {str(freq)+'%':>10s} {avg:>8s}  {read}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    mode, arg = sys.argv[1], sys.argv[2]
    if mode == "player":
        player(arg)
    elif mode == "team":
        team(arg)
    elif mode == "coverage":
        coverage(arg)
    elif mode == "matchup" and len(sys.argv) >= 4:
        matchup(arg, sys.argv[3])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
