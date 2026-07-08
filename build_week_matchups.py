#!/usr/bin/env python3
"""build_week_matchups.py — extract per-game GROUNDED facts for a given week from the
verified repo layers, so a matchup analysis is built on data (not model priors — CLAUDE.md §1).

For each game: environment (game_sim Vegas + sim + team_ceiling), each offense's identity/
pace/pass-rate/PROE, and the OPPONENT defense each attacks (coverage shell, by-position
softness, coverage splits, unit percentiles, funnel lean, 2026 scheme change), plus the
stack-menu angle. Matchup edge is player/offense strength × defense softness × coverage
frequency (C8) — never O/U alone (C5).

  python3 build_week_matchups.py --week 1  ->  analysis/week1_payloads.json
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def jload(*p):
    fp = os.path.join(HERE, *p)
    return json.load(open(fp)) if os.path.exists(fp) else None

def teamed(d):
    return d.get("teams", d) if isinstance(d, dict) else {}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--week", type=int, default=1)
    a = ap.parse_args(); W = str(a.week)

    gs = jload("game_sim.json") or {}
    games = (gs.get("weeks", {}).get(W, {}) or {}).get("games", [])
    if not games:
        print(f"FATAL: no games for week {W} in game_sim.json"); return 1

    dsplits = jload("defense_splits.json") or {}
    ceil = teamed(jload("team_ceiling.json") or {})
    off = jload("offense_profile.json") or {}
    proe = teamed(jload("proe_tendency_2026.json") or {})
    csch = teamed(jload("coordinator_scheme_2026.json") or {})
    stacks = teamed(jload("stack_menu.json") or {})
    wt = {t.get("team"): t for t in (jload("web_teams.json") or []) if isinstance(t, dict)}
    fullname = {}
    try:
        import brain.brain_common as bc  # noqa
    except Exception:
        pass

    def off_profile(ab):
        o = (off or {}).get(ab, {})
        return {"identity": o.get("identity", ""), "pass_rate": o.get("pass_rate"),
                "pace_pctl": (o.get("pace") or {}).get("pctl"),
                "run_scheme": (o.get("run_scheme") or {}).get("lean"),
                "win_total": (o.get("environment") or {}).get("win_total"),
                "off_q": (o.get("environment") or {}).get("off_q")}

    def def_profile(ab):
        """the defense the OTHER team attacks."""
        d = dsplits.get(ab, {})
        sh = d.get("shell") or {}
        bp = d.get("by_pos") or {}
        soft = sorted(((k, v) for k, v in bp.items() if isinstance(v, (int, float)) and v >= 3), key=lambda x: -x[1])
        sting = sorted(((k, v) for k, v in bp.items() if isinstance(v, (int, float)) and v <= -3), key=lambda x: x[1])
        cs = csch.get(ab, {})
        sc = None
        if cs.get("dc_new"):
            sc = {"dc": cs.get("dc_name"), "man_2025": cs.get("man_rate_2025"),
                  "man_adj": cs.get("man_rate_adj"), "conf": cs.get("conf")}
        return {
            "shell": {"man": sh.get("man_rate"), "single_high": sh.get("single_high"), "two_high": sh.get("two_high")},
            "soft_vs": [{"pos": k.upper(), "edge": round(v, 1)} for k, v in soft[:3]],
            "stingy_vs": [{"pos": k.upper(), "edge": round(v, 1)} for k, v in sting[:3]],
            "cover_splits": {kk: {"soft_pctl": (d.get(kk) or {}).get("softness_pctl"),
                                  "ypr": (d.get(kk) or {}).get("allowed_ypr")}
                             for kk in ("vs_man", "vs_zone", "deep", "short") if d.get(kk)},
            "units": d.get("units") or {},
            "funnels": (d.get("funnels") or [])[:2], "lean_2026": d.get("lean_2026"),
            "scheme_change_2026": sc,
        }

    out = []
    for g in games:
        teams = g.get("teams", [])
        if len(teams) != 2: continue
        h, aw = teams  # game_sim order
        v = g.get("vegas", {}); s = g.get("sim", {})
        imp = v.get("imp", {})
        card = {
            "game": g.get("game"), "home": h, "away": aw,
            "env": {"total": v.get("total"), "sim_median": s.get("median_total"),
                    "imp": {h: imp.get(h), aw: imp.get(aw)},
                    "spread_fav": v.get("spread_fav"), "spread": v.get("spread"),
                    "ceiling": {h: (ceil.get(h) or {}).get("ceiling_score"),
                                aw: (ceil.get(aw) or {}).get("ceiling_score")}},
            "sides": {}
        }
        for team, opp in ((h, aw), (aw, h)):
            card["sides"][team] = {
                "offense": off_profile(team),
                "proe_2026": (proe.get(team) or {}).get("proe_2026"),
                "attacks_defense": def_profile(opp),   # this team attacks opp's defense
                "stack": (lambda sm: {"tier": sm.get("tier"), "ceiling": sm.get("ceiling_score"),
                                       "w17_opp": sm.get("w17_opp")} if sm else None)(stacks.get(team)),
            }
        out.append(card)

    os.makedirs(os.path.join(HERE, "analysis"), exist_ok=True)
    dest = os.path.join(HERE, "analysis", f"week{W}_payloads.json")
    json.dump({"week": a.week, "games": out}, open(dest, "w"), indent=1)
    print(f"wrote {os.path.relpath(dest, HERE)}: {len(out)} games")
    # sanity print one game
    g0 = out[0]
    print(f"\nsample — {g0['game']}: O/U {g0['env']['total']} · sim {g0['env']['sim_median']} · "
          f"imp {g0['env']['imp']}")
    for t in (g0['home'], g0['away']):
        dp = g0['sides'][t]['attacks_defense']
        print(f"  {t} attacks: shell man {dp['shell']['man']}% · soft vs {[x['pos'] for x in dp['soft_vs']]} · lean {dp['lean_2026']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
