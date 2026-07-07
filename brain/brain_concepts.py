#!/usr/bin/env python3
"""brain_concepts.py — the CONCEPTS layer of the vault (the piece the entities/ + raw/ vault was
missing). One page per TEAM in Concepts/, capturing the reusable analytical THESES — how to value
and attack that team in 2026 — distilled from the model + brain and wikilinked to the team entity
page and its key players, so the knowledge graph compounds (a concept ↔ its team ↔ its players).

This is the "concepts/ = one page per idea (principle/playbook)" box from the second-brain workflow,
instantiated per team. Auto-content lives between markers and regenerates; your own observations go
under ## Notes and are never overwritten.

Sources (all repo layers): offense_profile.json + scheme_2026.json (offensive identity),
boom/defensive_profile.json + nflpro_2025.json (defensive funnel — attack/avoid lanes),
personnel_2026.json (personnel identity), game_sim.json + boom/statmenu.json (environment),
brain_intel.json (team + player forward theses), draft_board_signals.csv (player ranking).

  python3 brain/brain_concepts.py --vault ~/Downloads/NFL-Brain            # write Concepts/*.md
  python3 brain/brain_concepts.py --vault ... --repo ... --dry-run         # print one, write nothing
"""
import argparse, csv, json, os, sys
import brain_common as bc

MARK_A = "%% auto:concept:begin — refreshed by brain_concepts.py; your notes go under ## Notes, not here %%"
MARK_B = "%% auto:concept:end %%"

def load(repo, *parts):
    p = os.path.join(repo, *parts)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

def fn(n):
    import re
    n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    return n.replace(".", "").replace("'", "").replace("-", " ")

# curated top-line theses for teams analyzed in depth; others get a data-composed thesis (honest,
# from the funnel + environment + scheme, no invented narrative)
THESIS = {
 "ARI": "The teardown, priced. A 4.5-win team that the market makes an underdog in every simmed game — "
        "and chronic trailing manufactures pass-catcher volume. Two-TE base squeezes targets onto four "
        "players; the buy is the target monopoly ([[Trey McBride]]), the leverage is the cheap Brissett "
        "connection ([[Michael Wilson]]).",
}

def _off_concept(ab, off, wt, bteam):
    ident = (off or {}).get("identity", "") if off else ""
    note = (off or {}).get("scheme_note", "") if off else ""
    outlook = (wt or {}).get("offense_outlook", "")
    env = (off or {}).get("environment", {}) if off else {}
    parts = []
    if ident: parts.append(f"**Identity:** {ident}")
    if note and note not in ident: parts.append(f"**Scheme:** {note}")
    if outlook: parts.append(f"**2026:** {outlook}")
    if env.get("win_total"): parts.append(f"**Win total:** {env['win_total']} · off quality {env.get('off_q','–')} · env idx {env.get('env_idx','–')}")
    return "\n\n".join(parts)

EXTRAS = {}   # optional decision layers loaded in main(); every renderer degrades gracefully


def _shell(ab):
    ds = (EXTRAS.get("shell") or {}).get(ab, {})
    sh = ds.get("shell") or {}
    if not sh: return ""
    s = f"**Coverage shell (2025):** man {sh.get('man_rate','–')}% · single-high {sh.get('single_high','–')}% · two-high {sh.get('two_high','–')}%"
    bp = ds.get("by_pos") or {}
    if bp:
        soft = sorted(((k, v) for k, v in bp.items() if isinstance(v, (int, float)) and v >= 3), key=lambda x: -x[1])[:2]
        sting = sorted(((k, v) for k, v in bp.items() if isinstance(v, (int, float)) and v <= -3), key=lambda x: x[1])[:2]
        if soft: s += " · soft vs " + ", ".join(f"{k.upper()} (+{v:.0f})" for k, v in soft)
        if sting: s += " · stingy vs " + ", ".join(f"{k.upper()} ({v:.0f})" for k, v in sting)
    return s


def _ceiling_engine(ab):
    tc = (EXTRAS.get("ceiling") or {}).get(ab, {})
    pr = (EXTRAS.get("proe") or {}).get(ab, {})
    bits = []
    if tc.get("ceiling_score") is not None:
        dr = tc.get("drivers") or {}
        top = sorted(((k, v) for k, v in dr.items() if isinstance(v, (int, float)) and v > 0), key=lambda x: -x[1])[:3]
        bits.append(f"**Team ceiling engine:** {tc['ceiling_score']}" +
                    (" (top drivers: " + ", ".join(f"{k} {v:.2f}" for k, v in top) + ")" if top else ""))
    if pr.get("proe_2026") is not None:
        bits.append(f"**PROE 2026:** {pr['proe_2026']:+.1f}" + (f" — {pr['note']}" if pr.get("note") else ""))
    return "\n\n".join(bits)


def _stack_menu(ab):
    sm = (EXTRAS.get("stacks") or {}).get(ab)
    if not sm: return ""
    s = f"Ceiling **{sm.get('ceiling_score','–')} {sm.get('tier','')}** · W17 vs {sm.get('w17_opp','?')} (opp ceiling {sm.get('w17_opp_ceiling','–')} · game env {sm.get('w17_game_env','–')})"
    bb = sm.get("bringback") or []
    if bb:
        s += "\n\n**Bring-backs:** " + " · ".join(f"[[{b['name']}]] {b.get('pos','')} (ADP {b.get('adp',0):.0f})" for b in bb[:4])
    return s


def _def_concept(ab, dprof, ngs):
    out = []
    dp = (dprof or {}).get(ab, {})
    fpaa = dp.get("dvoa_fpaa", {})
    green = [k.upper() for k, v in fpaa.items() if isinstance(v, (int, float)) and v >= 1.5]
    red = [k.upper() for k, v in fpaa.items() if isinstance(v, (int, float)) and v <= -1.5]
    if green or red:
        line = "**Attack this defense via:** " + (", ".join(green) if green else "no clear soft lane")
        if red: line += f" · **avoid:** {', '.join(red)}"
        out.append(line)
    fun = dp.get("funnels", [])
    if fun: out.append("**Funnels (2025):** " + "; ".join(fun[:3]))
    lean = dp.get("lean_2026")
    if lean: out.append(f"**2026 engine lean:** {lean}-funnel")
    ng = (ngs or {}).get(ab, {}).get("pass", {}) if ngs else {}
    soft = {k: v.get("soft_pctl") for k, v in ng.items() if k != "ALL" and isinstance(v.get("soft_pctl"), (int, float))}
    if soft:
        tgt = [k for k, v in soft.items() if v >= 65]; avd = [k for k, v in soft.items() if v <= 35]
        s = "**NGS 2025 lanes (attacker view):** "
        s += ("target " + ", ".join(f"{k} {soft[k]}th" for k in tgt) if tgt else "no soft lane")
        if avd: s += " · wall " + ", ".join(f"{k} {soft[k]}th" for k in avd)
        out.append(s)
    sh = _shell(ab)
    if sh: out.append(sh)
    return "\n\n".join(out) if out else "_no funnel data_"

def _environment(ab, gs, statmenu):
    if not gs: return ""
    weeks = gs.get("weeks", {})
    imps, dogs, tot = [], 0, 0
    for wk in weeks.values():
        for g in wk.get("games", []):
            if ab in g["teams"]:
                v = g["vegas"]; imp = v["imp"].get(ab); imps.append(imp) if imp else None
                fav = v["spread_fav"]; line = -v["spread"] if fav == ab else v["spread"]
                if line > 0: dogs += 1
                tot += 1
    if not tot: return ""
    avg = sum(imps) / len(imps) if imps else 0
    tag = " — trails often; pass-catcher volume is manufactured" if dogs >= tot * 0.6 else (
          " — favored often; lead scripts feed the run game" if dogs <= tot * 0.35 else "")
    return f"Underdog in **{dogs}/{tot}** simmed games · avg implied **{avg:.1f}** pts{tag}."

def _personnel(ab, pers):
    p = (pers or {}).get(ab, {})
    if not p: return ""
    d = p.get("direction_2026"); arrow = {"up": "▲ trending heavier", "down": "▼ trending lighter"}.get(d, "")
    s = f"Heavy personnel **{p.get('heavy_2025','–')}%** (#{p.get('heavy_rank_2025','–')} in 2025) · PA {p.get('pa_2025','–')}% · motion {p.get('motion_2025','–')}% {arrow}".strip()
    fp = (EXTRAS.get("fp_pers") or {}).get(ab, {})
    if fp.get("heavy_rate") is not None:
        s += f" · FP charting cross-check: heavy {fp['heavy_rate']*100:.0f}%"
    # 2026 EXPECTATION from personnel_2026_projection.json (coordinator-change aware) —
    # previously built but never rendered: 2025 actuals showed with no 2026 direction
    pj = (EXTRAS.get("pers_proj") or {}).get(ab, {})
    prj = pj.get("projection_2026") or {}
    if prj.get("heavy_direction"):
        d = prj["heavy_direction"]
        arr = {"down": "▼ LIGHTER", "up": "▲ HEAVIER"}.get(d, d)
        why = prj.get("rationale") or ""
        s += f"\n\n**2026 projection: {arr}**" + (f" — {why}" if why else "")
        # FP-split lens: who is exposed to the shift. heavy_share = % of 2025 routes run
        # from heavy sets (FP charting). Lighter -> 3-WR routes grow, TE2/FB snaps shrink;
        # heavier -> the reverse. Deterministic exposure, not a projection of outcomes.
        fpl = EXTRAS.get("fp_players") or {}
        dep = sorted(((k.title(), v.get("pos", ""), v["heavy_share"]) for k, v in fpl.items()
                      if v.get("team") == ab and v.get("routes", 0) >= 150 and v.get("heavy_share") is not None),
                     key=lambda x: -x[2])
        if dep:
            s += "\n\n**FP-split exposure (2025 heavy-set route share):** " + \
                 " · ".join(f"{n} {p} {h*100:.0f}%" for n, p, h in dep[:6])
            s += ("\n→ lighter favors the 3-WR routes (low-% names above gain); high-% TE/FB usage is at risk"
                  if d == "down" else
                  "\n→ heavier favors the high-% names above; 3-WR-dependent routes are at risk")
    return s

def _players(ab, sig_by_team, brain):
    rows = sorted(sig_by_team.get(ab, []), key=lambda r: -(float(r.get("proj_pg") or 0)))[:6]
    out = []
    for r in rows:
        nm = r["name"]; b = brain.get(fn(nm), {})
        lean = (b.get("fwd") or [{}])[0].get("t", "") if b.get("fwd") else ""
        pos = r.get("pos", "")
        line = f"- [[{nm}]] ({pos})"
        if lean: line += f" — {lean[:150]}"
        out.append(line)
    return "\n".join(out)

def build_page(ab, full, data):
    off, wt, dprof, ngs, gs, pers, sig_by_team, brain, statmenu = data
    thesis = THESIS.get(ab)
    if not thesis:
        # compose an honest data thesis: environment + defensive funnel headline
        env = _environment(ab, gs, statmenu)
        thesis = (env + " " if env else "") + "See the funnel and player theses below for the attack map."
    body = f"""## Thesis
{thesis}

## Offensive concept — how they score
{_off_concept(ab, off, next((x for x in wt if x['team']==ab), {}), None)}

**Personnel:** {_personnel(ab, pers) or '_n/a_'}

## Defensive identity — how opponents attack them
{_def_concept(ab, dprof, ngs)}

## Environment
{_environment(ab, gs, statmenu) or '_n/a_'}

{_ceiling_engine(ab)}
{("## Stack menu" + chr(10) + _stack_menu(ab) + chr(10)) if _stack_menu(ab) else ""}
## Key player theses
{_players(ab, sig_by_team, brain) or '_none_'}"""
    fm = f"""---
type: concept
team: {ab}
scope: team-playbook
tags: [concept/team]
---

# {full} — Team Concept

> [!abstract] How to value & attack [[{full}]] in 2026 — the reusable theses, distilled from the model + brain. Auto-content regenerates; your own observations go under ## Notes and are never overwritten.
"""
    return fm, body

def upsert(vault, fname, fm, body):
    d = os.path.join(vault, "Concepts"); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, fname)
    block = f"{MARK_A}\n{body}\n{MARK_B}"
    if os.path.exists(path):
        cur = open(path, encoding="utf-8").read()
        if MARK_A in cur and MARK_B in cur:
            pre, rest = cur.split(MARK_A, 1); _, post = rest.split(MARK_B, 1)
            new = pre + block + post
        else:
            new = cur.rstrip() + "\n\n" + block + "\n"
    else:
        new = fm + "\n" + block + "\n\n## Notes\n%% append-only — your concepts/observations land here; the generator never edits below this line %%\n"
    open(path, "w", encoding="utf-8").write(new)
    return os.path.relpath(path, vault)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True); ap.add_argument("--repo", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault); repo = bc.repo_root(a.repo)
    wt = load(repo, "web_teams.json")
    off = load(repo, "offense_profile.json"); dprof = load(repo, "boom", "defensive_profile.json")
    ngs = (load(repo, "nflpro_2025.json") or {}).get("teams", {})
    gs = load(repo, "game_sim.json"); pers = (load(repo, "personnel_2026.json") or {}).get("teams", {})
    statmenu = load(repo, "boom", "statmenu.json")
    brain = {fn(k): v for k, v in (load(repo, "brain_intel.json") or {}).get("players", {}).items()}
    EXTRAS["shell"] = load(repo, "defense_splits.json") or {}
    EXTRAS["ceiling"] = (load(repo, "team_ceiling.json") or {}).get("teams", {})
    EXTRAS["proe"] = (load(repo, "proe_tendency_2026.json") or {}).get("teams", {})
    EXTRAS["stacks"] = (load(repo, "stack_menu.json") or {}).get("teams", {})
    EXTRAS["fp_pers"] = (load(repo, "fp_personnel.json") or {}).get("teams", {})
    _pp = load(repo, "personnel_2026_projection.json") or {}
    EXTRAS["pers_proj"] = _pp.get("teams", _pp)
    EXTRAS["fp_players"] = (load(repo, "fp_personnel.json") or {}).get("players", {})
    sig_by_team = {}
    for r in csv.DictReader(open(os.path.join(repo, "draft_board_signals.csv"))):
        sig_by_team.setdefault(r["team"], []).append(r)
    data = (off, wt, dprof, ngs, gs, pers, sig_by_team, brain, statmenu)

    teams = {t["team"]: t for t in wt}
    full_of = {ab: bc._TEAMS.get(ab, [ab])[0] for ab in teams}
    n = 0
    for ab, full in sorted(full_of.items()):
        fm, body = build_page(ab, full, data)
        if a.dry_run:
            if ab == "ARI":
                print(fm + "\n" + MARK_A + "\n" + body + "\n" + MARK_B)
            continue
        rel = upsert(vault, f"{full}.md", fm, body)
        n += 1
    bc.log(f"brain_concepts: {'dry-run (ARI shown)' if a.dry_run else f'{n} team concept pages written to Concepts/'}")
    print(json.dumps({"concepts": (0 if a.dry_run else n)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
