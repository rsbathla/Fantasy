#!/usr/bin/env python3
"""
gameplan.py  --  DraftKings Best Ball Mania 2026  --  Module C: Best-Ball Game Plan
Ceiling-first draft priority, team attack order, and QB+WR1+bring-back stacks.
Philosophy: MODEL FUSION + UPSIDE (p95 / spike / advance%, not mean).
Inputs (read-only): draft_board_signals.csv, team_review_data.json,
pipeline/correlation_structure.json, fusion_table.csv (optional).
Outputs (owned): gameplan.json, GAMEPLAN.md.
"""
import json
import os
import math
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def P(*a):
    print(*a)


ALPHA_P95 = 33.0
N_TIERS = 8
N_ROUNDS = 20
TEAMS_IN_LEAGUE = 12
N_STACKS = 15

W_P95 = 0.50
W_SPIKE = 0.25
W_ADV = 0.25

R_QB_WR1 = 0.351
R_QB_WR2 = 0.339
R_BRINGBACK_HIGH = 0.159
R_BRINGBACK_ALL = 0.129

AW_CEIL = 0.42
AW_ENV = 0.26
AW_PACE = 0.18
AW_VAC = 0.14

STACK_ADP_PENALTY = 0.0016


def zscore(series):
    s = pd.to_numeric(series, errors="coerce")
    mu = s.mean()
    sd = s.std(ddof=0)
    if not sd or math.isnan(sd) or sd == 0:
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - mu) / sd


def safe(v, default=0.0):
    try:
        if v is None:
            return default
        f = float(v)
        if math.isnan(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def r2num(x, nd=2):
    try:
        return round(float(x), nd)
    except (TypeError, ValueError):
        return None


def parse_w17(game):
    if not isinstance(game, str) or "@" not in game:
        return (None, None)
    away, home = game.split("@", 1)
    return (away.strip(), home.strip())


def load():
    board = pd.read_csv(os.path.join(HERE, "draft_board_signals.csv"))
    with open(os.path.join(HERE, "team_review_data.json")) as f:
        teams = json.load(f)
    with open(os.path.join(HERE, "pipeline", "correlation_structure.json")) as f:
        corr = json.load(f)
    fusion = None
    fpath = os.path.join(HERE, "fusion_table.csv")
    if os.path.exists(fpath):
        try:
            fusion = pd.read_csv(fpath)
        except Exception as e:
            P("[warn] could not read fusion_table.csv:", e)
            fusion = None
    return board, teams, corr, fusion


def enrich_board(board, fusion):
    df = board.copy()
    df["_has_signal"] = df["p95"].notna()
    for col in ("p95", "spike", "adv_pct"):
        df[col + "_f"] = df.groupby("pos")[col].transform(
            lambda s: s.fillna(s.min() if s.notna().any() else 0.0)
        )
    df["_z_p95"] = df.groupby("pos")["p95_f"].transform(zscore)
    df["_z_spike"] = df.groupby("pos")["spike_f"].transform(zscore)
    df["_z_adv"] = df.groupby("pos")["adv_pct_f"].transform(zscore)
    df["ceiling_score"] = (
        W_P95 * df["_z_p95"] + W_SPIKE * df["_z_spike"] + W_ADV * df["_z_adv"]
    )
    df.loc[~df["_has_signal"], "ceiling_score"] = np.nan
    df = df.sort_values("adp").reset_index(drop=True)
    df["adp_rank"] = np.arange(1, len(df) + 1)
    df["_gap"] = df["adp_rank"] - df["merged_rank"]
    VALUE_GAP = 12
    REACH_GAP = -15
    fmap = {}
    if fusion is not None:
        fcols = set(fusion.columns)
        for _, r in fusion.iterrows():
            tag = {}
            if "flags" in fcols and isinstance(r.get("flags"), str):
                tag["flags"] = r["flags"]
            if "divergence" in fcols:
                tag["divergence"] = safe(r.get("divergence"))
            if "ceiling_pctl" in fcols:
                tag["ceiling_pctl"] = safe(r.get("ceiling_pctl"))
            if "consensus" in fcols:
                tag["consensus"] = safe(r.get("consensus"))
            fmap[r["name"]] = tag

    def flags_for(row):
        out = []
        if row["_gap"] >= VALUE_GAP and row["_has_signal"]:
            out.append("VALUE")
        if row["_gap"] <= REACH_GAP:
            out.append("REACH")
        ft = fmap.get(row["name"], {})
        ff = ft.get("flags")
        if isinstance(ff, str):
            for piece in ff.split(";"):
                piece = piece.strip()
                if piece and piece not in out:
                    out.append(piece)
        return out

    df["flags"] = df.apply(flags_for, axis=1)
    df["_fusion"] = df["name"].map(lambda n: fmap.get(n, {}))
    return df


def build_tiers(df):
    bands = [
        (1, 12), (12, 24), (24, 42), (42, 66),
        (66, 96), (96, 126), (126, 156), (156, 192),
    ]
    band_labels = [
        "R1 anchors", "R2", "R3-mid3", "R4-mid5",
        "R6-8", "R8-mid10", "mid10-13", "R13-16",
    ]
    tiers = []
    for i, ((lo, hi), label) in enumerate(zip(bands, band_labels), start=1):
        sub = df[(df["adp"] >= lo) & (df["adp"] < hi)].copy()
        sub = sub.sort_values(
            ["_has_signal", "ceiling_score"], ascending=[False, False]
        )
        players = []
        for _, r in sub.iterrows():
            players.append({
                "name": r["name"], "pos": r["pos"], "team": r["team"],
                "adp": r2num(r["adp"], 1), "p95": r2num(r["p95"], 1),
                "spike": r2num(r["spike"], 3), "adv": r2num(r["adv_pct"], 3),
                "ceiling_score": r2num(r["ceiling_score"], 3), "flags": r["flags"],
            })
        tiers.append({
            "tier": i, "adp_band": str(lo) + "-" + str(hi - 1),
            "label": label, "n": len(players), "players": players,
        })
    return tiers


def _target_row(r, kind):
    return {
        "name": r["name"], "pos": r["pos"], "team": r["team"],
        "adp": r2num(r["adp"], 1), "p95": r2num(r["p95"], 1),
        "ceiling_score": r2num(r["ceiling_score"], 3),
        "merged_rank": r2num(r["merged_rank"], 0),
        "flags": r["flags"], "kind": kind,
    }


def build_round_targets(df):
    rt = {}
    for rnd in range(1, N_ROUNDS + 1):
        lo = (rnd - 1) * TEAMS_IN_LEAGUE + 1
        hi = rnd * TEAMS_IN_LEAGUE + 1
        band = df[(df["adp"] >= lo) & (df["adp"] < hi)].copy()
        band_signal = band[band["_has_signal"]].sort_values(
            "ceiling_score", ascending=False
        )
        targets = []
        for _, r in band_signal.head(5).iterrows():
            targets.append(_target_row(r, kind="ceiling"))
        fallers = band[
            band["_has_signal"]
            & (band["merged_rank"] <= lo - 6)
            & (band["_gap"] >= 8)
        ].sort_values("ceiling_score", ascending=False)
        values = []
        seen = set(t["name"] for t in targets)
        for _, r in fallers.head(2).iterrows():
            if r["name"] in seen:
                for t in targets:
                    if t["name"] == r["name"]:
                        t["value_fall"] = True
                continue
            values.append(_target_row(r, kind="value"))
        rt[str(rnd)] = {
            "round": rnd, "adp_band": str(lo) + "-" + str(hi - 1),
            "targets": targets, "values": values,
        }
    return rt


def _team_why(r):
    bits = []
    if r["n_alpha_ceil"] >= 3:
        bits.append(str(int(r["n_alpha_ceil"])) + " alpha-ceiling bats (sum p95 " + ("%.0f" % r["sum_p95_alpha"]) + ")")
    elif r["n_alpha_ceil"] >= 1:
        bits.append(str(int(r["n_alpha_ceil"])) + " alpha ceiling(s) (sum p95 " + ("%.0f" % r["sum_p95_alpha"]) + ")")
    else:
        bits.append("thin on alpha ceilings")
    if r["rk_td"] <= 6:
        bits.append("elite scoring env (TD/g " + ("%.2f" % r["total_td"]) + ", rk" + str(int(r["rk_td"])) + ")")
    elif r["rk_td"] <= 12:
        bits.append("good scoring env (TD/g " + ("%.2f" % r["total_td"]) + ")")
    if r["rk_passvol"] <= 6:
        bits.append("top pass volume (rk" + str(int(r["rk_passvol"])) + ")")
    elif r["rk_passvol"] >= 24:
        bits.append("run-leaning (low pass volume)")
    if r["vac_tgt"] >= 30:
        bits.append("huge vacated targets (" + ("%.0f" % r["vac_tgt"]) + ")")
    elif r["vac_tgt"] >= 18:
        bits.append("notable vacated targets (" + ("%.0f" % r["vac_tgt"]) + ")")
    return "; ".join(bits)


def build_team_priority(df, teams):
    real_teams = [t for t in teams if t not in ("FA", "_league")]
    rows = []
    for t in real_teams:
        o = teams[t]
        script = o.get("script", {})
        delta = o.get("delta", {})
        bteam = df[(df["team"] == t) & (df["_has_signal"])]
        alpha = bteam[bteam["p95"] >= ALPHA_P95]
        rows.append({
            "team": t,
            "nalpha_review": o.get("nalpha"),
            "n_alpha_ceil": len(alpha),
            "sum_p95_alpha": float(alpha["p95"].sum()),
            "top4_p95": float(bteam.sort_values("p95", ascending=False)["p95"].head(4).sum()),
            "total_td": safe(script.get("total_td")),
            "rk_td": safe(script.get("rk_td"), 16),
            "pass_att": safe(script.get("pass_att_pg")),
            "rk_passvol": safe(script.get("rk_passvol"), 16),
            "plays": safe(script.get("plays_pg")),
            "rk_plays": safe(script.get("rk_plays"), 16),
            "vac_tgt": safe(delta.get("vac_tgt")),
            "w17": o.get("w17"),
        })
    tp = pd.DataFrame(rows)

    def inv_rank_z(col):
        good = 33.0 - pd.to_numeric(tp[col], errors="coerce").clip(1, 32)
        return zscore(good)

    ceil_capital = (
        0.45 * zscore(tp["n_alpha_ceil"])
        + 0.35 * zscore(tp["sum_p95_alpha"])
        + 0.20 * zscore(tp["top4_p95"])
    )
    env = 0.6 * zscore(tp["total_td"]) + 0.4 * inv_rank_z("rk_td")
    pace = (
        0.45 * zscore(tp["pass_att"])
        + 0.30 * inv_rank_z("rk_passvol")
        + 0.25 * zscore(tp["plays"])
    )
    vac = zscore(tp["vac_tgt"])
    tp["c_ceil"] = ceil_capital
    tp["c_env"] = env
    tp["c_pace"] = pace
    tp["c_vac"] = vac
    tp["attack_raw"] = (
        AW_CEIL * ceil_capital + AW_ENV * env + AW_PACE * pace + AW_VAC * vac
    )
    lo, hi = tp["attack_raw"].min(), tp["attack_raw"].max()
    rng = (hi - lo) or 1.0
    tp["attack_score"] = ((tp["attack_raw"] - lo) / rng * 100).round(1)
    tp = tp.sort_values("attack_raw", ascending=False).reset_index(drop=True)
    tp["rank"] = np.arange(1, len(tp) + 1)
    out = []
    for _, r in tp.iterrows():
        out.append({
            "rank": int(r["rank"]), "team": r["team"],
            "attack_score": float(r["attack_score"]),
            "nalpha": int(r["n_alpha_ceil"]),
            "sum_p95_alpha": r2num(r["sum_p95_alpha"], 1),
            "total_td": r2num(r["total_td"], 2), "rk_td": int(r["rk_td"]),
            "rk_passvol": int(r["rk_passvol"]), "vac_tgt": r2num(r["vac_tgt"], 1),
            "why": _team_why(r),
        })
    return out, tp


def _team_total_td_map(teams):
    return {t: safe(teams[t].get("script", {}).get("total_td"))
            for t in teams if t not in ("FA", "_league")}


def _piece(r):
    return {
        "name": r["name"], "pos": r["pos"], "team": r["team"],
        "adp": r2num(r["adp"], 1), "p95": r2num(r["p95"], 1),
    }


def _leverage_tag(qb, adp_cost, is_high):
    qb_adp = safe(qb["adp"])
    tags = []
    if qb_adp >= 95 or adp_cost >= 230:
        tags.append("LEVERAGE")
    elif qb_adp <= 60 and adp_cost <= 150:
        tags.append("CHALK")
    else:
        tags.append("MID")
    if is_high:
        tags.append("SHOOTOUT")
    return "/".join(tags)


def _stack_note(qb, wr1, wr2, bring, opp, is_high, tail_rank):
    parts = [qb["name"] + " + " + wr1["name"]]
    if wr2 is not None:
        parts.append("(+" + wr2["name"] + ")")
    if bring is not None:
        parts.append("bring-back " + bring["name"] + " (" + str(opp) + ")")
    env = "shootout-tilted W17" if is_high else "moderate-total W17"
    tail = ("top-" + str(tail_rank) + " blow-up tail") if tail_rank <= 12 else ("tail rk" + str(tail_rank))
    return " ".join(parts) + " | " + env + ", " + tail + "."


def build_stacks(df, teams):
    tt = _team_total_td_map(teams)
    combos = []
    for g in df["w17_game"].dropna().unique():
        a, b = parse_w17(g)
        if a in tt and b in tt:
            combos.append(tt[a] + tt[b])
    high_total_cut = float(np.median(combos)) if combos else 4.5
    sig = df[df["_has_signal"]].copy()

    def recv_in_team(team):
        return sig[(sig["team"] == team) & (sig["pos"].isin(["WR", "TE"]))].sort_values(
            "p95", ascending=False
        )

    qbs = sig[sig["pos"] == "QB"].sort_values("adp")
    stacks = []
    for _, qb in qbs.iterrows():
        team = qb["team"]
        recv = recv_in_team(team)
        if recv.empty:
            continue
        wr1 = recv.iloc[0]
        rest = recv[recv["name"] != wr1["name"]]
        wr2 = rest.iloc[0] if not rest.empty else None
        game = qb["w17_game"]
        away, home = parse_w17(game)
        opp = None
        if away and home:
            opp = home if away == team else (away if home == team else None)
        bring = None
        bring_team = None
        if opp:
            opp_recv = recv_in_team(opp)
            if not opp_recv.empty:
                bring = opp_recv.iloc[0]
                bring_team = opp
        combined = tt.get(team, 0) + (tt.get(opp, 0) if opp else 0)
        is_high = combined >= high_total_cut
        r_bring = R_BRINGBACK_HIGH if is_high else R_BRINGBACK_ALL
        pieces = [_piece(qb), _piece(wr1)]
        include_wr2 = False
        if wr2 is not None and safe(wr2["p95"]) >= 28:
            pieces.append(_piece(wr2))
            include_wr2 = True
        members_bring = _piece(bring) if bring is not None else None
        combined_ceiling = sum(safe(p["p95"]) for p in pieces)
        if members_bring:
            combined_ceiling += safe(members_bring["p95"])
        adp_cost = sum(safe(p["adp"]) for p in pieces)
        if members_bring:
            adp_cost += safe(members_bring["adp"])
        corr_mult = 1.0 + R_QB_WR1
        if include_wr2:
            corr_mult += R_QB_WR2
        if members_bring:
            corr_mult += r_bring
        corr_factor = corr_mult / (1.0 + R_QB_WR1)
        tail_rank = int(safe(qb["w17_blowup_rank"], 99))
        score = combined_ceiling * corr_factor
        score *= (1.0 - STACK_ADP_PENALTY * adp_cost)
        if tail_rank <= 6:
            score *= 1.03
        leverage = _leverage_tag(qb, adp_cost, is_high)
        note = _stack_note(qb, wr1, wr2 if include_wr2 else None,
                           members_bring, opp, is_high, tail_rank)
        stacks.append({
            "qb": qb["name"], "team": team,
            "pieces": [p["name"] for p in pieces],
            "pieces_detail": pieces,
            "bringback": members_bring["name"] if members_bring else None,
            "bringback_team": bring_team, "w17_game": game,
            "tail_rank": tail_rank, "r_qbwr": R_QB_WR1,
            "r_bringback": r_bring if members_bring else None,
            "high_total": bool(is_high),
            "combined_ceiling": round(combined_ceiling, 1),
            "adp_cost": round(adp_cost, 1),
            "corr_factor": round(corr_factor, 3),
            "leverage": leverage, "score": round(score, 2), "note": note,
        })
    stacks.sort(key=lambda s: s["score"], reverse=True)
    for i, s in enumerate(stacks, start=1):
        s["rank"] = i
    return stacks[:N_STACKS], high_total_cut


def write_markdown(tiers, round_targets, team_priority, stacks, meta):
    L = []
    L.append("# DraftKings Best Ball Mania 2026 - GAME PLAN")
    L.append("")
    L.append("*Module C of the toolkit. Ceiling-first. Built for the tournament shape: "
             "top-2 of 12 advance the W1-14 grind, then W15/16/17 playoff gates into a "
             "top-heavy W17 final. Everything below is graded on **upside (p95 / spike / "
             "advance%)**, not mean projection. Philosophy: **model fusion** - show what "
             "each signal says, don't overfit.*")
    L.append("")
    L.append("- Players scored: **" + str(meta["n_scored"]) + "** of " + str(meta["n_board"]) +
             " on the board (deep depth with no ceiling signal excluded from tiers).")
    L.append("- Alpha-ceiling threshold: **p95 >= " + ("%.0f" % ALPHA_P95) + "**.")
    L.append("- ceiling_score = " + ("%.2f" % W_P95) + "*z(p95) + " + ("%.2f" % W_SPIKE) +
             "*z(spike) + " + ("%.2f" % W_ADV) + "*z(adv%) - z **within position**.")
    L.append("- W17 bring-back r: **" + str(R_BRINGBACK_HIGH) + "** when the finals game is "
             "a shootout (combined team TD/g >= " + ("%.2f" % meta["high_total_cut"]) +
             "), else **" + str(R_BRINGBACK_ALL) + "**. QB-WR1 r = **" + str(R_QB_WR1) + "**.")
    L.append("")
    L.append("## 1. Ceiling-First Draft Priority")
    L.append("")
    L.append("Tiers are **ADP bands** (a tier = an ADP range worth prioritising for "
             "ceiling), ordered **within the band by ceiling_score** so the spike outcomes "
             "float to the top. `VALUE` = board model rank beats the market (fell to you); "
             "`REACH` = market is paying ahead of the model.")
    L.append("")
    for t in tiers:
        L.append("### Tier " + str(t["tier"]) + " - ADP " + t["adp_band"] + " (" +
                 t["label"] + ") - " + str(t["n"]) + " players")
        L.append("")
        L.append("| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |")
        L.append("|---:|---|:--:|:--:|---:|---:|---:|---:|---|")
        for i, p in enumerate(t["players"][:12], start=1):
            fl = ", ".join(p["flags"]) if p["flags"] else ""
            adv = (("%.0f%%" % (p["adv"] * 100)) if isinstance(p["adv"], (int, float)) else "-")
            L.append("| " + str(i) + " | " + p["name"] + " | " + p["pos"] + " | " + p["team"] +
                     " | " + str(p["adp"]) + " | " + str(p["p95"]) + " | " + adv + " | " +
                     str(p["ceiling_score"]) + " | " + fl + " |")
        if t["n"] > 12:
            L.append("| ... | *+" + str(t["n"] - 12) + " more in band* | | | | | | | |")
        L.append("")
    L.append("## 1b. Round-by-Round Targets (12-team snake)")
    L.append("")
    L.append("For each round (ADP band of 12), the best **ceiling targets** in-band, plus "
             "**values falling** from earlier (model rank says they belong sooner). A star "
             "(*) marks a target that is itself a fallen value.")
    L.append("")
    for rnd in range(1, N_ROUNDS + 1):
        d = round_targets[str(rnd)]
        L.append("**Round " + str(rnd) + "** (ADP " + d["adp_band"] + ")")
        tline = []
        for t in d["targets"]:
            star = "*" if t.get("value_fall") else ""
            tline.append(t["name"] + star + " (" + t["pos"] + "-" + t["team"] + ", p95 " + str(t["p95"]) + ")")
        L.append("- Ceiling: " + ("; ".join(tline) if tline else "-"))
        if d["values"]:
            vline = [v["name"] + " (" + v["pos"] + "-" + v["team"] + ", mrank " + str(int(v["merged_rank"])) + ")"
                     for v in d["values"]]
            L.append("- Value falling: " + "; ".join(vline))
        L.append("")
    L.append("## 2. Team Priority - Attack Order (32 offenses)")
    L.append("")
    L.append("Attack score = " + ("%.2f" % AW_CEIL) + "*ceiling-capital + " + ("%.2f" % AW_ENV) +
             "*scoring-env + " + ("%.2f" % AW_PACE) + "*pass-volume/pace + " + ("%.2f" % AW_VAC) +
             "*vacated-opportunity (each z-scored across the 32 teams, then scaled 0-100). "
             "Attack the top of this list when ceiling capital is scarce on the clock.")
    L.append("")
    L.append("| Rank | Team | Attack | a-ceil | Sum p95(a) | TD/g | rk_TD | rk_passvol | vac_tgt | Why |")
    L.append("|---:|:--:|---:|:--:|---:|---:|:--:|:--:|---:|---|")
    for r in team_priority:
        L.append("| " + str(r["rank"]) + " | " + r["team"] + " | " + str(r["attack_score"]) +
                 " | " + str(r["nalpha"]) + " | " + str(r["sum_p95_alpha"]) + " | " +
                 str(r["total_td"]) + " | " + str(r["rk_td"]) + " | " + str(r["rk_passvol"]) +
                 " | " + str(r["vac_tgt"]) + " | " + r["why"] + " |")
    L.append("")
    L.append("## 3. Stacks - QB + WR1 (+WR2/TE) + Week-17 Bring-Back")
    L.append("")
    L.append("A stack pairs a QB with his top pass-catcher(s) and a **bring-back** receiver "
             "from the **Week-17 finals opponent** (the correlated game where the title is "
             "decided). WR1 = the team's highest-p95 pass-catcher (the alpha the QB-WR1 r "
             "was measured on). Combined ceiling = sum of members' p95. Stack score = "
             "combined ceiling x correlation factor, lightly penalised by total ADP cost; "
             "top-tail (rk<=6) shootouts get a small bonus. `LEVERAGE` = cheaper / "
             "lower-profile; `CHALK` = premium; `SHOOTOUT` = high-total game.")
    L.append("")
    L.append("| Rank | QB | Team | Pieces | Bring-back | W17 game | Tail | r(bb) | "
             "Comb. ceil | ADP cost | Lev | Score |")
    L.append("|---:|---|:--:|---|---|:--:|:--:|---:|---:|---:|---|---:|")
    for s in stacks:
        pcs = " + ".join(s["pieces"])
        bb = (s["bringback"] + " (" + str(s["bringback_team"]) + ")") if s["bringback"] else "-"
        rbb = str(s["r_bringback"]) if s["r_bringback"] is not None else "-"
        L.append("| " + str(s["rank"]) + " | " + s["qb"] + " | " + s["team"] + " | " + pcs +
                 " | " + bb + " | " + str(s["w17_game"]) + " | " + str(s["tail_rank"]) + " | " +
                 rbb + " | " + str(s["combined_ceiling"]) + " | " + str(s["adp_cost"]) + " | " +
                 s["leverage"] + " | " + str(s["score"]) + " |")
    L.append("")
    L.append("### Stack notes")
    for s in stacks:
        L.append("- **#" + str(s["rank"]) + " " + s["qb"] + " (" + s["team"] + ")** - " +
                 s["note"] + " Combined ceiling " + str(s["combined_ceiling"]) + ", ADP cost " +
                 str(s["adp_cost"]) + ", corr factor " + str(s["corr_factor"]) + ", score " +
                 str(s["score"]) + ".")
    L.append("")
    lev = [s for s in stacks if "LEVERAGE" in s["leverage"]]
    if lev:
        L.append("### Explicit leverage stacks (cheaper / lower-profile)")
        for s in lev:
            extra = (", " + ", ".join(s["pieces"][1:])) if len(s["pieces"]) > 1 else ""
            bbtxt = (" + " + s["bringback"]) if s["bringback"] else ""
            L.append("- **" + s["qb"] + " (" + s["team"] + ")**" + extra + bbtxt +
                     " - ADP cost " + str(s["adp_cost"]) + ", combined ceiling " +
                     str(s["combined_ceiling"]) + ", " + s["leverage"] + ".")
        L.append("")
    L.append("---")
    L.append("*Generated by `gameplan.py`. Read-only on shared inputs; this module owns "
             "`gameplan.py`, `gameplan.json`, `GAMEPLAN.md` only.*")
    return "\n".join(L)


def verify(df, tiers, round_targets, team_priority, tp_df, stacks, teams, high_cut):
    P("\n" + "=" * 78)
    P("VERIFICATION")
    P("=" * 78)
    board_names = set(df["name"])
    team_of = dict(zip(df["name"], df["team"]))
    all_tier_players = [p["name"] for t in tiers for p in t["players"]]
    missing = [n for n in all_tier_players if n not in board_names]
    P("[tiers] total tiered players: " + str(len(all_tier_players)) + " | unique: " +
      str(len(set(all_tier_players))) + " | not-on-board: " + str(len(missing)))
    if missing:
        P("   !! missing:", missing[:10])
    top180 = set(df.sort_values("adp").head(180)["name"])
    covered = top180 & set(all_tier_players)
    P("[tiers] draftable top-180 covered by tiers: " + str(len(covered)) + "/180 (" +
      ("%.0f" % (len(covered) / 180 * 100)) + "%)")
    P("   tier sizes: " + ", ".join("T" + str(t["tier"]) + "=" + str(t["n"]) for t in tiers))
    empties = [r for r in range(1, N_ROUNDS + 1) if not round_targets[str(r)]["targets"]]
    P("[rounds] rounds 1-" + str(N_ROUNDS) + " built | rounds with no ceiling target: " +
      (str(empties) if empties else "none"))
    for rr in (1, 5, 10):
        d = round_targets[str(rr)]
        P("   R" + str(rr) + " (" + d["adp_band"] + "): " +
          ", ".join(t["name"] for t in d["targets"]))
    P("[teams] ranked " + str(len(team_priority)) + " offenses (expect 32): " +
      ("OK" if len(team_priority) == 32 else "CHECK"))
    rank_of = {r["team"]: r["rank"] for r in team_priority}
    for t in ["DET", "CIN", "BAL", "PHI"]:
        sc = next((r["attack_score"] for r in team_priority if r["team"] == t), "?")
        P("   " + t + " attack rank: " + str(rank_of.get(t, "?")) + " (score " + str(sc) + ")")
    loaded_top = all(rank_of.get(t, 99) <= 16 for t in ["DET", "CIN", "BAL"])
    P("   loaded offenses (DET/CIN/BAL) all in top-16: " + str(loaded_top))
    P("   --- TOP 12 TEAM PRIORITY ---")
    for r in team_priority[:12]:
        P("   %2d. %-3s score %5s | a-ceil %d Sp95 %5s | TD/g %s (rk%s) | passvol rk%s | vac %s" % (
            r["rank"], r["team"], r["attack_score"], r["nalpha"], r["sum_p95_alpha"],
            r["total_td"], r["rk_td"], r["rk_passvol"], r["vac_tgt"]))
    P("   --- STACK INTEGRITY CHECK ---")
    bad = 0
    for s in stacks:
        team = s["team"]
        if team_of.get(s["qb"]) != team:
            P("   !! " + s["qb"] + " not on " + team + " (on " + str(team_of.get(s["qb"])) + ")")
            bad += 1
        for pn in s["pieces"][1:]:
            if team_of.get(pn) != team:
                P("   !! piece " + pn + " not on " + team)
                bad += 1
        if s["bringback"]:
            away, home = parse_w17(s["w17_game"])
            opp = home if away == team else (away if home == team else None)
            if team_of.get(s["bringback"]) != opp:
                P("   !! bring-back " + s["bringback"] + " not on W17 opp " + str(opp) +
                  " (on " + str(team_of.get(s["bringback"])) + ")")
                bad += 1
            if s["bringback_team"] != opp:
                P("   !! bringback_team " + str(s["bringback_team"]) + " != computed opp " + str(opp))
                bad += 1
    P("   stack integrity problems: " + str(bad))
    P("   high-total cut (combined team TD/g): " + ("%.2f" % high_cut))
    P("   --- TOP 10 STACKS ---")
    for s in stacks[:10]:
        bb = (s["bringback"] + "(" + str(s["bringback_team"]) + ")") if s["bringback"] else "no-bb"
        P("   %2d. %-16s [%s] %s >> %-22s | W17 %-8s tl%-2s | ceil %5s adp %6s | %-14s score %s" % (
            s["rank"], s["qb"], s["team"], " + ".join(s["pieces"][1:]), bb,
            s["w17_game"], s["tail_rank"], s["combined_ceiling"], s["adp_cost"],
            s["leverage"], s["score"]))
    P("=" * 78)
    return {"tier_missing": len(missing), "stack_problems": bad, "top180_cov": len(covered)}


def main():
    board, teams, corr, fusion = load()
    nt = len([t for t in teams if t not in ("FA", "_league")])
    P("[load] board=" + str(len(board)) + " players | teams=" + str(nt) +
      " | fusion=" + ("yes" if fusion is not None else "no"))
    df = enrich_board(board, fusion)
    n_scored = int(df["_has_signal"].sum())
    tiers = build_tiers(df)
    round_targets = build_round_targets(df)
    team_priority, tp_df = build_team_priority(df, teams)
    stacks, high_cut = build_stacks(df, teams)
    meta = {
        "n_board": len(df), "n_scored": n_scored, "alpha_p95": ALPHA_P95,
        "high_total_cut": high_cut, "r_qb_wr1": R_QB_WR1, "r_qb_wr2": R_QB_WR2,
        "r_bringback_high": R_BRINGBACK_HIGH, "r_bringback_all": R_BRINGBACK_ALL,
        "weights": {
            "ceiling_score": {"p95": W_P95, "spike": W_SPIKE, "adv": W_ADV},
            "attack": {"ceil": AW_CEIL, "env": AW_ENV, "pace": AW_PACE, "vac": AW_VAC},
        },
    }
    out = {
        "meta": meta, "draft_tiers": tiers, "round_targets": round_targets,
        "team_priority": team_priority, "stacks": stacks,
    }
    with open(os.path.join(HERE, "gameplan.json"), "w") as f:
        json.dump(out, f, indent=2)
    P("[write] gameplan.json (" + str(os.path.getsize(os.path.join(HERE, "gameplan.json"))) + " bytes)")
    md = write_markdown(tiers, round_targets, team_priority, stacks, meta)
    with open(os.path.join(HERE, "GAMEPLAN.md"), "w", encoding="utf-8") as f:
        f.write(md)
    P("[write] GAMEPLAN.md (" + str(len(md)) + " chars)")
    verify(df, tiers, round_targets, team_priority, tp_df, stacks, teams, high_cut)


if __name__ == "__main__":
    main()
