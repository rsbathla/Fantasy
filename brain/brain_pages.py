#!/usr/bin/env python3
"""brain_pages.py — generate the entity pages of the brain: one note per PLAYER, TEAM, and COACH,
each with an auto-built "## Model read" from the repo's verified quant layers. This is what makes
every [[wikilink]] in the captured tweets/articles/videos resolve to a real page whose backlinks
pane is the player's full intel trail.

Three-zone discipline (from the original vault design):
  ## Model read   — AUTO-GENERATED between markers; refreshed on every run from repo layers
  ## Intel log    — append-only, yours + brain_link's; NEVER touched by this script
  ## Notes        — freeform; NEVER touched

Safety: content is only ever replaced BETWEEN the auto markers. A page that exists but has no
markers (e.g. a hand-made prototype note) is SKIPPED and reported, never overwritten.

  python3 brain/brain_pages.py --vault ~/Downloads/NFL-Brain [--repo PATH]
"""
import argparse
import json
import os
import re
import sys

import brain_common as bc

MARK_A = "%% auto:model-read:begin — refreshed by brain_pages.py; edit below the end marker, not here %%"
MARK_B = "%% auto:model-read:end %%"
TRAIL_A = "%% auto:mention-trail:begin — every tweet/source note mentioning this player; refreshed by brain_pages.py %%"
TRAIL_B = "%% auto:mention-trail:end %%"

import glob as _glob

def build_mention_index(vault):
    """One pass over the vault's Tweets/ and Sources/ notes -> {display name: [records]}.
    This is the FULL trail (the export caps highlights; the vault does not)."""
    tw_idx, src_idx = {}, {}
    def fm_fields(txt):
        parts = txt.split("---", 2)
        if len(parts) < 3: return None, ""
        return parts[1], parts[2]
    for p in _glob.glob(os.path.join(vault, "Tweets", "*", "*.md")):
        head, body = fm_fields(open(p, encoding="utf-8").read())
        if head is None or "mentions:" not in head: continue
        ments = re.findall(r"\[\[([^\]]+)\]\]", head.split("mentions:", 1)[1].split("\n", 1)[0])
        d = re.search(r"^date:\s*(\S+)", head, re.M)
        a = re.search(r'^author:\s*"?(@[\w]+)', head, re.M)
        ql = [l[2:] for l in body.split("\n") if l.startswith("> ") and not l.startswith("> [!")]
        text = " ".join(" ".join(ql).split())          # FULL tweet text — the trail is the record
        rec = (d.group(1) if d else "", a.group(1) if a else "", os.path.splitext(os.path.basename(p))[0], text)
        for m in ments: tw_idx.setdefault(m, []).append(rec)
    for p in _glob.glob(os.path.join(vault, "Sources", "*.md")):
        head, body = fm_fields(open(p, encoding="utf-8").read())
        if head is None or "mentions:" not in head: continue
        ments = re.findall(r"\[\[([^\]]+)\]\]", head.split("mentions:", 1)[1].split("\n", 1)[0])
        d = re.search(r"^date:\s*(\S+)", head, re.M)
        ty = re.search(r"^type:\s*(\S+)", head, re.M)
        ot = re.search(r'^outlet:\s*"?([^"\n]+)', head, re.M)
        base = os.path.splitext(os.path.basename(p))[0]
        # search the PROSE only — the note body embeds its own **Mentions:** wikilink block,
        # which would otherwise always match first and quote the useless name list
        if "**Mentions:**" in body:
            _pre, _rest = body.split("**Mentions:**", 1)
            _k = _rest.find("---")
            body = _pre + (_rest[_k + 3:] if _k >= 0 else "")
        # what THIS source said about each player: the window around his name mention.
        # Surname fallback only when unique among this source's mentions (Brown collision).
        surname_ct = {}
        for m in ments:
            t = m.split()[-1]
            if len(t) >= 5: surname_ct[t] = surname_ct.get(t, 0) + 1
        for m in ments:
            j = body.find(m)
            if j < 0:
                t = m.split()[-1]
                if len(t) >= 5 and surname_ct.get(t) == 1: j = body.find(t)
            ex = ""
            if j >= 0:
                ex = " ".join(body[max(0, j - 120):j + 300].split()).replace("[[", "").replace("]]", "")
                if j > 120: ex = "…" + ex
                if len(ex) > 380: ex = ex[:380] + "…"
            src_idx.setdefault(m, []).append(
                (d.group(1) if d else "", ty.group(1) if ty else "source", base,
                 (ot.group(1).strip() if ot else ""), ex))
    for idx in (tw_idx, src_idx):
        for k in idx: idx[k].sort(key=lambda r: r[0], reverse=True)
    return tw_idx, src_idx


def render_trail(nm, tw_idx, src_idx):
    tws, srcs = tw_idx.get(nm, []), src_idx.get(nm, [])
    if not tws and not srcs: return ""
    L = []
    if tws:
        L.append(f"### Tweets ({len(tws)})")
        for d, a, base, text in tws:
            L.append(f"- **{d}** {a} — {text} → [[{base}]]")
    if srcs:
        L.append(f"\n### Sources ({len(srcs)})")
        for d, ty, base, outlet, ex in srcs:
            line = f"- {d} · {ty}" + (f" · {outlet}" if outlet else "")
            if ex: line += f" — “{ex}”"
            L.append(line + f" → [[{base}]]")
    return "\n".join(L)


def upsert_trail(page_path, trail):
    """Insert/replace the '## Mention trail' managed zone (before ## Notes)."""
    if not trail or not os.path.exists(page_path): return
    txt = open(page_path, encoding="utf-8").read()
    block = f"## Mention trail\n{TRAIL_A}\n{trail}\n{TRAIL_B}"
    if TRAIL_A in txt and TRAIL_B in txt:
        pre, rest = txt.split(TRAIL_A, 1); _, post = rest.split(TRAIL_B, 1)
        new = pre + TRAIL_A + "\n" + trail + "\n" + TRAIL_B + post
    else:
        i = txt.find("## Notes")
        new = (txt[:i] + block + "\n\n" + txt[i:]) if i >= 0 else txt + "\n" + block + "\n"
    if new != txt:
        open(page_path, "w", encoding="utf-8").write(new)


def fmt(v, nd=1):
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return None


def pct(v):
    f = fmt(v, 0)
    return f"{f}th pctl" if f is not None else None


def _fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    n = n.replace('.', '').replace("'", '').replace('-', ' '); return ' '.join(n.split())


def player_best_worst(v, sc, spl, pf_entry):
    """One-glance Best/Worst synthesis from the layers already computed: coverage spec,
    man/zone lean, alignment wins-from, favorable/tough playoff weeks, weak scenario dims."""
    best, worst = [], []
    cs = v.get("cspec") or {}
    if cs.get("best"):
        best.append(f"vs {cs['best']} ({pct(cs.get('pctl'))})")
    if spl:
        lean = spl.get("man_lean")
        if lean == "zone": worst.append("man-heavy Ds")
        elif lean == "man": worst.append("zone-heavy Ds")
        for w in (spl.get("weeks") or []):
            tgt = best if w.get("v") == "FAV" else worst
            tgt.append(f"W{str(w.get('wk','')).lstrip('W')} {w.get('opp')}" + (f" ({w['why']})" if w.get("why") else ""))
    af = (pf_entry or {}).get("alignment_funnel") or {}
    if af.get("wins_from"):
        best.insert(0, f"{af['wins_from']} alignment")
    dims = (sc or {}).get("sources") or {}
    weak = [(k, x) for k, x in dims.items() if isinstance(x, (int, float)) and x < 40 and not k.startswith("environment_w")]
    for k, x in sorted(weak, key=lambda t: t[1])[:2]:
        worst.append(f"{k} ({x:.0f} pctl)")
    strong = [(k, x) for k, x in dims.items() if isinstance(x, (int, float)) and x >= 90 and not k.startswith("environment_w")]
    for k, x in sorted(strong, key=lambda t: -t[1])[:3]:
        best.append(f"{k} ({x:.0f} pctl)")
    drv = (sc or {}).get("drivers") or {}
    if isinstance(drv.get("sis_boom"), (int, float)) and drv["sis_boom"] >= 35:
        best.append(f"SIS boom {drv['sis_boom']:.0f}%")
    if isinstance(drv.get("sis_bust"), (int, float)) and drv["sis_bust"] >= 20:
        worst.append(f"SIS bust {drv['sis_bust']:.0f}%")
    rz = v.get("_rz_equity") or {}
    if isinstance(rz.get("rz_role_z"), (int, float)):
        if rz["rz_role_z"] >= 0.5: best.append(f"red-zone role (z+{rz['rz_role_z']:.1f})")
        elif rz["rz_role_z"] <= -0.5: worst.append(f"thin red-zone role (z{rz['rz_role_z']:.1f})")
    L = []
    if best: L.append("- **Best:** " + " · ".join(best[:7]))
    if worst: L.append("- **Worst:** " + " · ".join(worst[:6]))
    return L


def player_tweet_intel(intel_entry, n=5):
    """The actual discussion — newest scored tweets about this player from the brain export."""
    tws = (intel_entry or {}).get("tw") or []
    if not tws:
        return []
    recent = sorted(tws, key=lambda t: t.get("d", ""), reverse=True)[:n]
    L = ["- **Tweet intel (latest):**"]
    for t in recent:
        txt = " ".join(str(t.get("t", "")).split())[:190]
        url = t.get("u")
        L.append(f"    - {t.get('d','?')} {t.get('a','')}: {txt}" + (f" [↗]({url})" if url else ""))
    return L


def player_scenario_read(sc, spl, fpp_entry):
    """Render the decision layers: dfs_scenarios (5-source ceiling consensus + W15-17 spike
    probabilities), player_splits (playoff-week matchup verdicts + style profile), and
    fp_personnel (how tied he is to heavy sets)."""
    L = []
    if sc:
        prof = sc.get("profile") or ""
        cc = sc.get("ceiling_consensus"); dv = sc.get("ceiling_divergence")
        if cc is not None:
            s = f"- **Ceiling consensus:** {fmt(cc)} pctl ({sc.get('n_sources', '?')} sources · divergence {fmt(dv)})"
            if prof: s += f" — {prof}"
            L.append(s)
        pw = [(w, sc.get(f"p_w{w}")) for w in (15, 16, 17)]
        if any(p is not None for _, p in pw):
            L.append("- **Spike prob (playoff wks):** " + " · ".join(
                f"W{w} {p*100:.0f}%" for w, p in pw if p is not None))
    if spl:
        tags = spl.get("profile")
        if isinstance(tags, str) and tags.startswith("["):   # stringified list in the source JSON
            tags = [t.strip(" '\"") for t in tags.strip("[]").split(",") if t.strip(" '\"")]
        if isinstance(tags, list) and tags:
            lean = spl.get("man_lean")
            L.append("- **Profile:** " + " · ".join(tags) + (f" · better vs {lean}" if lean else ""))
        wks = spl.get("weeks") or []
        if wks:
            bits = []
            for w in wks:
                mark = "✓" if w.get("v") == "FAV" else "✗"
                bits.append(f"W{str(w.get('wk','')).lstrip('W')} {w.get('opp')} {mark}{w.get('v')}" +
                            (f" ({w['why']})" if w.get("why") else ""))
            L.append("- **Playoff matchups:** " + " · ".join(bits))
    if fpp_entry:
        mix = fpp_entry.get("personnel_mix") or {}
        hs = fpp_entry.get("heavy_share")
        if mix:
            top = sorted(mix.items(), key=lambda x: -x[1])[:2]
            s = " · ".join(f"{k}P {v*100:.0f}%" for k, v in top)
            if hs is not None: s += f" · heavy sets {hs*100:.0f}% of routes"
            L.append(f"- **Personnel usage:** {s}")
    return L


def player_funnel_read(pf_entry, fp_entry, vintage):
    """Render the scraped per-player funnel layers (player_funnels.json — NGS alignment/depth/
    rushing; fp_alignment.json — FantasyPoints two-source cross-check). This is the weekly
    self-correcting blend's path to a human: preseason it shows 2025, in-season the blend."""
    L = []
    if not pf_entry:
        return L
    r = pf_entry.get("recv") or {}
    if r.get("yprr") is not None:
        bits = [f"{fmt(r['yprr'], 2)} YPRR", f"{fmt(r.get('routes_pg'))} rt/g" if r.get("routes_pg") else None,
                f"CROE {fmt(r['croe'])}" if r.get("croe") is not None else None,
                f"sep {fmt(r['avg_sep'], 2)}" if r.get("avg_sep") is not None else None]
        L.append(f"- **Route data ({vintage}):** " + " · ".join(b for b in bits if b))
    af = pf_entry.get("alignment_funnel") or {}
    mix = af.get("mix") or {}
    if mix:
        top = sorted(mix.items(), key=lambda x: -x[1])[:2]
        s = " / ".join(f"{k} {v*100:.0f}%" for k, v in top)
        if af.get("home"): s += f" · home {af['home']}"
        if af.get("wins_from") and af.get("wins_from") != af.get("home"):
            y = (af.get("yprr_by") or {}).get(af["wins_from"])
            s += f" · **wins from {af['wins_from']}**" + (f" ({fmt(y, 1)} YPRR)" if y else "")
        L.append(f"- **Alignment:** {s}")
    ru = pf_entry.get("rush") or {}
    if ru.get("att_pg") is not None:
        bits = [f"{fmt(ru['att_pg'])} att/g", f"{fmt(ru.get('ypc'), 2)} YPC" if ru.get("ypc") else None,
                f"RYOE/att {fmt(ru['ryoe_att'], 2)}" if ru.get("ryoe_att") is not None else None,
                f"YACO {fmt(ru['yaco_att'], 2)}" if ru.get("yaco_att") is not None else None]
        L.append(f"- **Rushing ({vintage}):** " + " · ".join(b for b in bits if b))
    if fp_entry and fp_entry.get("xcheck") == "diverge":
        L.append("- **⚠ Charting cross-check:** FP vs NGS alignment DIVERGE — read alignment with caution")
    return L


def player_model_read(v, team_full, refresh=None):
    L = []
    bits = [v.get("pos"), f"[[{team_full}]]" if team_full else v.get("team"), ]
    adp = fmt(v.get("adp"))
    if adp:
        asof = (refresh or {}).get("adp_asof")
        bits.append(f"ADP {adp}" + (f" (as of {asof})" if asof else ""))
    L.append(" · ".join(b for b in bits if b))
    # availability first — for W15-17 survival grading nothing else matters if he can't play
    av = v.get("avail") or {}
    if av.get("term"):
        L.append(f"- **⚠ Availability:** {av['term']} in the news ({av.get('n', 1)} mention{'s' if av.get('n', 1) != 1 else ''}, latest {av.get('d', '?')}) — check before drafting")
    sc = v.get("sched") or {}
    if sc.get("w17"):
        sbits = [f"bye W{sc['bye']}" if sc.get("bye") else None,
                 f"W15 {sc['w15']}" if sc.get("w15") else None,
                 f"W16 {sc['w16']}" if sc.get("w16") else None,
                 f"W17 {sc['w17']}" if sc.get("w17") else None]
        L.append("- **Playoff path:** " + " · ".join(b for b in sbits if b))
    boom = v.get("base_blended") if v.get("base_blended") is not None else v.get("base_boom")
    if boom is not None:
        L.append(f"- **Boom (blended):** {fmt(boom, 3)}" + (f" — {v.get('n_games')} gms charted" if v.get("n_games") else ""))
    fus = v.get("fus") or {}
    fbits = [f"value {pct(fus.get('value_pctl'))}" if fus.get("value_pctl") is not None else None,
             f"ceiling {pct(fus.get('ceiling_pctl'))}" if fus.get("ceiling_pctl") is not None else None]
    fbits = [b for b in fbits if b]
    if fbits:
        L.append(f"- **FUS:** " + " · ".join(fbits))
    u = v.get("usage") or {}
    ubits = []
    if u.get("tgt_share"): ubits.append(f"tgt share {fmt(u['tgt_share']*100)}%")
    if u.get("carry_share"): ubits.append(f"carry share {fmt(u['carry_share']*100)}%")
    if u.get("dk_pg"): ubits.append(f"{fmt(u['dk_pg'])} DK/gm")
    if ubits:
        # rookies never played 2025 — their numbers are projections, not actuals (quant audit:
        # "Usage (2025)" on a 2026 rookie is a factual-clause violation)
        is_rookie = bool(v.get("rookie_boost")) or (v.get("g25") in (0, None) and v.get("n_games") in (0, None))
        label = "Usage (proj — rookie)" if is_rookie else "Usage (2025)"
        L.append(f"- **{label}:** " + " · ".join(ubits))
    a = v.get("adot") or {}
    if a.get("TPRR"):
        s = f"- **TPRR:** {fmt(a['TPRR'], 3)}"
        if a.get("surplus_TPRR") is not None: s += f" (surplus {fmt(a['surplus_TPRR'], 3)})"
        if a.get("aDOT") is not None: s += f" · aDOT {fmt(a['aDOT'])}"
        L.append(s)
    c = v.get("cspec") or {}
    if c.get("best"):
        L.append(f"- **Coverage spec:** best vs {c['best']} ({pct(c.get('pctl'))})")
    rz = v.get("rz") or {}
    if rz.get("ez_td_pg") is not None:
        L.append(f"- **Red zone:** {fmt(rz['ez_td_pg'], 2)} EZ TD/gm · RZ tgt share {rz.get('rz_tgt_share')}%")
    te = v.get("team_env") or {}
    if te.get("win_total") is not None:
        L.append(f"- **Environment:** win total {te['win_total']} · env idx {te.get('env_idx')} · off quality {te.get('off_q')}")
    L.extend(v.get("_funnel_lines") or [])
    return "\n".join(L)


def team_model_read(t, sch, cc):
    L = []
    hc, oc, dc = t.get("hc"), t.get("oc"), t.get("dc")
    coach_bits = [f"HC [[{hc}]]" if hc else None, f"OC [[{oc}]]" if oc else None, f"DC [[{dc}]]" if dc else None]
    L.append(" · ".join(b for b in coach_bits if b))
    if t.get("win_total_2026") is not None:
        L.append(f"- **Win total:** {t['win_total_2026']}")
    s = sch.get(t["team"]) or {}
    if s.get("playcaller"):
        L.append(f"- **Play-caller:** {s['playcaller']}" + (f" — {s.get('note')}" if s.get("note") else ""))
    if s.get("def_note"):
        L.append(f"- **Defense:** {s['def_note']}")
    e = cc.get(t["team"]) or {}
    if e.get("dc_scheme") and not s.get("def_note"):
        L.append(f"- **Defense:** {e['dc_scheme']}")
    if t.get("key_additions"):
        L.append(f"- **Key adds:** " + ", ".join(t["key_additions"][:4]))
    if t.get("key_losses"):
        L.append(f"- **Key losses:** " + ", ".join(t["key_losses"][:4]))
    if t.get("offense_outlook"):
        L.append(f"- **Offense:** {t['offense_outlook']}")
    if t.get("defense_outlook"):
        L.append(f"- **Defense outlook:** {t['defense_outlook']}")
    return "\n".join(L)


def coach_model_read(name, role, team_abbr, team_full, sch):
    role_full = {"hc": "Head coach", "oc": "Offensive coordinator", "dc": "Defensive coordinator"}[role]
    L = [f"{role_full} · [[{team_full}]]"]
    s = sch.get(team_abbr) or {}
    if role in ("hc", "oc") and s.get("playcaller") and name.split()[-1].lower() in s["playcaller"].lower():
        L.append(f"- **Calls the offense:** {s['playcaller']}" + (f" — {s.get('note')}" if s.get("note") else ""))
    if role in ("hc", "dc") and s.get("dc") and name.split()[-1].lower() in str(s.get("dc")).lower():
        L.append(f"- **Defense:** {s.get('def_note') or s.get('dc')}")
    return "\n".join(L)


def upsert(vault, subdir, name, frontmatter, model_read, created, updated, skipped):
    d = os.path.join(vault, subdir)
    os.makedirs(d, exist_ok=True)
    fname = bc.slug(name, 80) + ".md"
    # preserve apostrophes etc. via slug? slug strips them — keep display name in H1; filename slugged
    p = os.path.join(d, fname)
    block = f"{MARK_A}\n{model_read}\n{MARK_B}"
    if os.path.exists(p):
        cur = open(p, encoding="utf-8").read()
        if MARK_A in cur and MARK_B in cur:
            pre, rest = cur.split(MARK_A, 1)
            _, post = rest.split(MARK_B, 1)
            new = pre + MARK_A + "\n" + model_read + "\n" + MARK_B + post
            if new != cur:
                open(p, "w", encoding="utf-8").write(new)
                updated.append(f"{subdir}/{fname}")
            return
        skipped.append(f"{subdir}/{fname}")   # exists without markers (hand-made) — never touch
        return
    content = f"""---
{frontmatter}
---

# {name}

## Model read
{block}

## Intel log
%% append-only — dated, sourced items land here (yours + brain_link's). brain_pages never edits this zone. %%

## Notes

"""
    open(p, "w", encoding="utf-8").write(content)
    created.append(f"{subdir}/{fname}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)

    sm = json.load(open(os.path.join(repo, "boom", "statmenu.json")))
    wt = json.load(open(os.path.join(repo, "web_teams.json")))
    sch = json.load(open(os.path.join(repo, "scheme_2026.json")))
    sch = {k: v for k, v in sch.items() if not k.startswith("_")}
    cc = json.load(open(os.path.join(repo, "coordinator_changes_2026.json")))
    cc = {k: v for k, v in cc.items() if not k.startswith("_")}
    team_full = {k: v[0] for k, v in bc._TEAMS.items()}
    alias_rev = {}
    for al, disp in bc._ALIASES.items():
        alias_rev.setdefault(disp, []).append(al)

    created, updated, skipped = [], [], []

    refresh = sm.get("_refresh") if isinstance(sm.get("_refresh"), dict) else {}

    # scraped per-player layers (optional — pages degrade gracefully without them)
    pf, pf_vint, fpa = {}, "2025", {}
    pfp = os.path.join(repo, "player_funnels.json")
    if os.path.exists(pfp):
        _pf = json.load(open(pfp))
        pf = _pf.get("players", _pf)
        pf_vint = (_pf.get("_meta") or {}).get("vintage") or "2025"
    fap = os.path.join(repo, "fp_alignment.json")
    if os.path.exists(fap):
        fpa = json.load(open(fap)).get("players", {})
    # decision layers: scenario engine, playoff matchup splits, FP personnel
    scen, spls, fpp = {}, {}, {}
    dsp = os.path.join(repo, "dfs_scenarios.json")
    if os.path.exists(dsp):
        for e in json.load(open(dsp)).get("players", []):
            if isinstance(e, dict) and e.get("name"): scen[_fn(e["name"])] = e
    psp = os.path.join(repo, "player_splits.json")
    if os.path.exists(psp):
        spls = {k: v for k, v in json.load(open(psp)).items() if isinstance(v, dict)}
    fppp = os.path.join(repo, "fp_personnel.json")
    if os.path.exists(fppp):
        fpp = json.load(open(fppp)).get("players", {})
    # tweet highlights: brain_intel.json is written BEFORE pages in both run scripts
    intel = {}
    bip = os.path.join(repo, "brain_intel.json")
    if os.path.exists(bip):
        intel = {_fn(k): e for k, e in json.load(open(bip)).get("players", {}).items()}
    rzp = os.path.join(repo, "rz_equity_2026.json")
    rzq = {}
    if os.path.exists(rzp):
        rzq = json.load(open(rzp)).get("teams", {})   # keyed by normalized player name
    tw_idx, src_idx = build_mention_index(vault)      # the FULL vault trail, uncapped

    # ---- players ----
    for v in sm.values():
        if not isinstance(v, dict):
            continue
        nm = v.get("name")
        if not nm:
            continue
        k = _fn(nm)
        v["_rz_equity"] = rzq.get(k)
        v["_funnel_lines"] = (player_best_worst(v, scen.get(k), spls.get(k), pf.get(k))
                              + player_scenario_read(scen.get(k), spls.get(k), fpp.get(k))
                              + player_funnel_read(pf.get(k), fpa.get(k), pf_vint)
                              + player_tweet_intel(intel.get(k)))
        tf = team_full.get(v.get("team"))
        aliases = list(alias_rev.get(nm, []))
        if bc.slug(nm, 80) != nm:
            aliases.insert(0, nm)   # filename loses apostrophes etc. — alias makes [[Ja'Marr Chase]] resolve
        fm = [f'type: player', f'position: {v.get("pos", "")}', f'team: {v.get("team", "")}',
              f'tags: [entity/player]']
        if aliases:
            fm.insert(1, "aliases: [" + ", ".join(f'"{x}"' for x in aliases) + "]")
        upsert(vault, "Players", nm, "\n".join(fm), player_model_read(v, tf, refresh), created, updated, skipped)
        upsert_trail(os.path.join(vault, "Players", bc.slug(nm, 80) + ".md"), render_trail(nm, tw_idx, src_idx))

    # ---- teams ----
    for t in wt:
        tf = team_full.get(t["team"])
        if not tf:
            continue
        fm = [f'type: team', f'abbr: {t["team"]}', f'tags: [entity/team]']
        upsert(vault, "Teams", tf, "\n".join(fm), team_model_read(t, sch, cc), created, updated, skipped)

    # ---- coaches ----
    seen = set()
    for t in wt:
        for role in ("hc", "oc", "dc"):
            nm = (t.get(role) or "").strip()
            if not nm or nm in seen:
                continue
            seen.add(nm)
            tf = team_full.get(t["team"], t["team"])
            fm = [f'type: coach', f'role: {role.upper()}', f'team: {t["team"]}', f'tags: [entity/coach]']
            if bc.slug(nm, 80) != nm:
                fm.insert(1, f'aliases: ["{nm}"]')   # e.g. Kevin O'Connell -> Kevin OConnell.md
            upsert(vault, "Coaches", nm, "\n".join(fm), coach_model_read(nm, role, t["team"], tf, sch),
                   created, updated, skipped)

    bc.log(f"pages: {len(created)} created · {len(updated)} refreshed · {len(skipped)} skipped (hand-made, no markers)")
    for s in skipped[:10]:
        bc.log(f"  skipped: {s}")
    print(json.dumps({"created": len(created), "updated": len(updated), "skipped": len(skipped)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
