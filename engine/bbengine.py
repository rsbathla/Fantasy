"""bbengine.py — clean, importable engine API for the NFL Best Ball 2026 draft tool (Contract 1).

Wraps the validated pipeline (sim_prod / survival_chain / win_delta) behind a run-dir-agnostic
interface. The pipeline scripts use RELATIVE paths (survival_chain.py does open('sim_prod.py'),
open('games_by_week.json'), etc.), so every call into the engine is wrapped in a chdir into
pipeline/ (saved/restored via a contextmanager + try/finally). Import or run this from anywhere
(the bestball/ root, the engine/ dir, or an absolute path) and it resolves correctly.

Public API
----------
load_board() -> list[dict]
    Every draftable player: {name,sim_name,pos,team,adp,rank,proj,ceiling_p95,bye,playoff_up}.
grade(rosters, me="rsbathla") -> dict
    {p_adv,surv_W15,surv_W16,win_W17,title_share,anchor} for `me`, via survival_chain.chain.
pick_values(rosters, me, candidates, ns=1500) -> {name:{dadv,dtitle,dw17}}
    Marginal title/adv/W17 contribution of each candidate, via win_delta.win_deltas.
parse_board(text, seat) -> {pick,round,seat,my_roster,counts,available}
    Parse a DK draft board (live names OR pre-draft pos/team-only resolved via ADP), reusing the
    logic from ../draft_pick.py + ../draft_assistant.py.
canon(name, pos=None) -> str | None
    Resolve a board player name to its Clay/sim canonical name (recovers first-name variants like
    "Kenneth Walker III" -> "Ken Walker III"), or None when no safe match exists.
"""
from __future__ import annotations

import os
import re
import sys
import json
import contextlib

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Path resolution — make the engine run-dir agnostic.
# ---------------------------------------------------------------------------
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_ENGINE_DIR)                 # bestball/
_PIPELINE_DIR = os.path.join(_REPO_ROOT, "pipeline")      # bestball/pipeline/


def _repo(*parts: str) -> str:
    """Absolute path under the bestball/ repo root."""
    return os.path.join(_REPO_ROOT, *parts)


def _pipe(*parts: str) -> str:
    """Absolute path under bestball/pipeline/."""
    return os.path.join(_PIPELINE_DIR, *parts)


@contextlib.contextmanager
def _in_pipeline():
    """Run a block with cwd == pipeline/ so the pipeline's relative open()/read_csv() resolve.

    The original working directory is always restored, even on exception. We also make sure
    pipeline/ is importable on sys.path so `import survival_chain` works regardless of caller cwd.
    """
    prev = os.getcwd()
    if _PIPELINE_DIR not in sys.path:
        sys.path.insert(0, _PIPELINE_DIR)
    os.chdir(_PIPELINE_DIR)
    try:
        yield
    finally:
        os.chdir(prev)


# ---------------------------------------------------------------------------
# Lazy import of the heavy pipeline modules (they exec sim_prod.py on import, which
# runs a 12k-sample build). Import them once, inside pipeline/, and cache.
# ---------------------------------------------------------------------------
_sc = None   # survival_chain module
_wd = None   # win_delta module


def _load_engine_modules():
    """Import survival_chain + win_delta exactly once, from within pipeline/."""
    global _sc, _wd
    if _sc is not None and _wd is not None:
        return _sc, _wd
    with _in_pipeline():
        import survival_chain as sc          # noqa: E402  (relative-path side effects)
        import win_delta as wd                # noqa: E402
    _sc, _wd = sc, wd
    return _sc, _wd


def _norm(n: str) -> str:
    """Name normalization identical to survival_chain._norm / draft_assistant.fn.

    Lower, strip suffixes (Jr/Sr/II/III/IV/V), drop '.' / "'" / '-' (-> space), collapse spaces.
    Self-contained so load_board / parse_board work without importing the heavy sim modules.
    """
    n = str(n).strip().lower()
    n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    n = n.replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(n.split())


# ===========================================================================
# canon — safe board-name -> Clay/sim canonical name resolver
# ===========================================================================
# THE BUG (fixed here): board player names don't always match the Clay/sim projection names, so
# real players were silently excluded from grading. The root cause is FIRST-NAME variants, not
# suffixes (suffixes already strip in _norm). Examples that _norm alone misses:
#   "Kenneth Walker III"  -> norm "kenneth walker" != "ken walker"      (Clay: "Ken Walker III")
#   "Cam Ward"            -> norm "cam ward"       != "cameron ward"    (Clay: "Cameron Ward")
#   "Chig Okonkwo"        -> "chig okonkwo"        != "chigoziem okonkwo"
#   "Joshua Palmer"       -> "joshua palmer"       != "josh palmer"
#
# A naive (first-initial, last-name) fallback is UNSAFE — it manufactures FALSE matches between
# genuinely different players that share a last name (and, here, a first initial / first letters):
#   "Keenan Allen"    must NOT map to "Kaytron Allen"
#   "J'Mari Taylor"   must NOT map to "Jonathan Taylor"
#   "Kyle Williams"   must NOT map to "Kyren Williams"
#   "Brandon Allen"   must NOT map to "Braelon Allen"     (different position too)
#   "Jamaal Williams" must NOT map to "Jameson Williams"
#
# The safe rule (see canon() below): exact normalized match wins; otherwise, among Clay names with
# the SAME normalized last name AND SAME token count, accept a candidate only if the first names are
# COMPATIBLE and EXACTLY ONE candidate is compatible. "Compatible" = prefix relation (ken/kenneth,
# cam/cameron, josh/joshua) OR shared first 3 letters (nic/nic for nick/nicholas, where prefix fails)
# OR Levenshtein edit distance <= 1. When a position is known (it is at the load_board chokepoint),
# we additionally require the candidate to share that position, which rejects same-last-name/
# same-first-letters collisions across positions (Brandon Allen[QB] vs Braelon Allen[RB]).
_NORM2CLAY = None       # {norm_clay_name: clay_display_name}  (from survival_chain.NORM2CLAY)
_CLAY_BY_LAST = None    # {(ntok, last_token): [(norm_clay, clay_display), ...]}
_CLAY_POS = None        # {clay_display_name: pos}  (for the optional same-position guard)
_BOARD_POS = None       # {norm_board_name: pos}    (lazy; lets bare canon(name) self-resolve pos)
_CANON_CACHE = None     # {(norm_name, pos): clay_display_or_None}


def _levenshtein(a: str, b: str) -> int:
    """Edit distance between two short strings (iterative DP, O(len(a)*len(b)))."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def _first_compatible(f1: str, f2: str) -> bool:
    """Two first names are 'compatible' (likely the same person's first name) iff:
    one is a prefix of the other (ken/kenneth, cam/cameron, josh/joshua, chig/chigoziem),
    OR they share the first 3 letters (nick/nicholas -> nic == nic; prefix fails there),
    OR their Levenshtein edit distance is <= 1.
    """
    if not f1 or not f2:
        return False
    if f1 == f2:
        return True
    if f1.startswith(f2) or f2.startswith(f1):
        return True
    if len(f1) >= 3 and len(f2) >= 3 and f1[:3] == f2[:3]:
        return True
    return _levenshtein(f1, f2) <= 1


def _build_canon_index():
    """Build (once) the Clay/sim name index from survival_chain.NORM2CLAY (the sim universe).

    NORM2CLAY maps norm(clay_name) -> clay_name; its VALUES are the canonical sim names. We bucket
    them by (token-count, last-token) so the fuzzy fallback only ever compares same-structure,
    same-last-name candidates. We also capture each Clay name's position for the same-position guard.
    """
    global _NORM2CLAY, _CLAY_BY_LAST, _CLAY_POS
    if _NORM2CLAY is not None:
        return _NORM2CLAY, _CLAY_BY_LAST, _CLAY_POS
    sc, _ = _load_engine_modules()
    _NORM2CLAY = dict(sc.NORM2CLAY)
    by_last: dict = {}
    for nk, disp in _NORM2CLAY.items():
        parts = nk.split()
        if not parts:
            continue
        by_last.setdefault((len(parts), parts[-1]), []).append((nk, disp))
    _CLAY_BY_LAST = by_last
    # Clay position map: survival_chain exposes name2pos (clay_name -> QB/RB/WR/TE).
    _CLAY_POS = dict(getattr(sc, "name2pos", {}) or {})
    return _NORM2CLAY, _CLAY_BY_LAST, _CLAY_POS


def _board_pos_index() -> dict:
    """Lazy {norm_board_name: pos} so a bare canon(name) can self-resolve the player's position
    for the same-position guard. Built from load_board() (which passes pos explicitly to canon and
    therefore does NOT re-enter this index — no recursion). Cached."""
    global _BOARD_POS
    if _BOARD_POS is not None:
        return _BOARD_POS
    bp: dict = {}
    for p in load_board():
        bp.setdefault(_norm(p["name"]), p.get("pos"))
    _BOARD_POS = bp
    return _BOARD_POS


def canon(name: str, pos: str | None = None) -> str | None:
    """Resolve a board player name to its Clay/sim canonical name, or None if no safe match.

    Rule:
      1. Exact normalized match (existing _norm) wins.
      2. Otherwise, among Clay names with the SAME normalized last name AND same token count,
         keep candidates whose first name is COMPATIBLE (_first_compatible). If `pos` is known
         (or self-resolved from the board), additionally require the candidate to share `pos`.
         Accept the match only if EXACTLY ONE candidate survives; if zero or >1 survive, return None.

    This recovers ken/kenneth, cam/cameron, chig/chigoziem, josh/joshua, nick/nicholas, while
    rejecting keenan/kaytron, jmari/jonathan, kyle/kyren, brandon/braelon, jamaal/jameson.
    """
    norm2clay, by_last, clay_pos = _build_canon_index()
    k = _norm(name)
    if not k:
        return None
    # (1) exact normalized match.
    if k in norm2clay:
        return norm2clay[k]
    # Self-resolve position from the board when not supplied (keeps a single safe chokepoint:
    # grade()/pick_values() can call canon(name) and still get the same-position guard for free).
    if pos is None:
        pos = _board_pos_index().get(k)
    cache = globals().get("_CANON_CACHE")
    if cache is None:
        cache = {}
        globals()["_CANON_CACHE"] = cache
    ck = (k, pos)
    if ck in cache:
        return cache[ck]
    parts = k.split()
    first = parts[0]
    cands = by_last.get((len(parts), parts[-1]), [])
    compat = [disp for nk, disp in cands if _first_compatible(first, nk.split()[0])]
    if pos is not None:
        compat = [d for d in compat if clay_pos.get(d) == pos]
    result = compat[0] if len(compat) == 1 else None
    cache[ck] = result
    return result


# ===========================================================================
# load_board
# ===========================================================================
# Cleaned column reads (the upload CSV carries trailing junk columns + Instructions text).
_MERGED_COLS = ["ID", "Name", "Position", "ADP", "Team"]


def _read_merged_rankings() -> pd.DataFrame:
    """merged_rankings_upload.csv -> name/pos/team/adp/rank.

    The file's *row order* is the pre-draft merged ranking (ID column drives the upload order,
    Gibbs #1, ...), so rank := 1-based row position. ADP is present for ~371 of 1568 rows.
    """
    df = pd.read_csv(_pipe("merged_rankings_upload.csv"))
    df = df[[c for c in _MERGED_COLS if c in df.columns]].copy()
    df = df.dropna(subset=["Name"])
    df = df.rename(columns={"Name": "name", "Position": "pos", "Team": "team", "ADP": "adp"})
    df["team"] = df["team"].replace({"LA": "LAR"})
    df["rank"] = range(1, len(df) + 1)            # file order == merged rank
    df["key"] = df["name"].map(_norm)
    df = df.drop_duplicates(subset="key", keep="first")
    return df[["name", "pos", "team", "adp", "rank", "key"]]


def _read_dk_adp() -> pd.DataFrame:
    """dk_adp.csv (repo root) -> per-name ADP, the canonical DK draft ADP. Falls back gracefully."""
    path = _repo("dk_adp.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["key", "adp_dk", "pos_dk", "team_dk", "name_dk"])
    df = pd.read_csv(path)
    df = df[["Name", "Position", "ADP", "Team"]].dropna(subset=["ADP"]).copy()
    df["Team"] = df["Team"].replace({"LA": "LAR"})
    df["key"] = df["Name"].map(_norm)
    df = df.rename(columns={"ADP": "adp_dk", "Position": "pos_dk", "Team": "team_dk", "Name": "name_dk"})
    df = df.drop_duplicates(subset="key", keep="first")
    return df[["key", "adp_dk", "pos_dk", "team_dk", "name_dk"]]


def _read_proj(platform: str = "DK") -> dict:
    """Projected per-game points -> {norm_name: pts}. Platform-aware:
       DK -> clay_2026.csv  (dk_pg, full-PPR)
       UD -> clay_2026_ud.csv (ud_pg, half-PPR)
    Falls back to clay_2026.csv/dk_pg if the platform file/column is absent."""
    plat = (platform or "DK").upper()
    fname = "clay_2026_ud.csv" if plat == "UD" else "clay_2026.csv"
    col = "ud_pg" if plat == "UD" else "dk_pg"
    path = _pipe(fname) if os.path.exists(_pipe(fname)) else _pipe("clay_2026.csv")
    df = pd.read_csv(path)
    if col not in df.columns:
        col = "dk_pg" if "dk_pg" in df.columns else None
    if col is None:
        return {}
    out = {}
    for nm, v in zip(df["name"], df[col]):
        out.setdefault(_norm(nm), v)
    return out


def _impute_missing_proj(rows: list) -> int:
    """Close the projection-coverage hole: a draftable player with an ADP but no projection
    (stars Clay omits — e.g. Tyreek Hill, Stefon Diggs, Brandon Aiyuk) is UNGRADEABLE and silently
    ignored by the sim. Impute their per-game projection from a POSITION-AWARE ADP->proj curve fit on
    players who have both, so every draftable player is gradeable in the correct scoring scale.
    Imputed players are flagged proj_src='adp_curve'. Returns count imputed."""
    import bisect
    by_pos = {}
    for r in rows:
        if r.get("proj") is not None and r.get("adp") is not None:
            by_pos.setdefault(r["pos"], []).append((float(r["adp"]), float(r["proj"])))
    anchors = {}
    for pos, pairs in by_pos.items():
        pairs.sort()
        adps = [a for a, _ in pairs]; projs = [p for _, p in pairs]
        for i in range(1, len(projs)):
            projs[i] = min(projs[i], projs[i - 1])   # isotonic-lite: proj non-increasing in ADP
        anchors[pos] = (adps, projs)
    allpairs = sorted((a, p) for pp in by_pos.values() for a, p in pp)
    g_adps = [a for a, _ in allpairs]; g_projs = [p for _, p in allpairs]
    for i in range(1, len(g_projs)):
        g_projs[i] = min(g_projs[i], g_projs[i - 1])

    def interp(adps, projs, x):
        if not adps:
            return None
        if x <= adps[0]:
            return projs[0]
        if x >= adps[-1]:
            return projs[-1]
        j = bisect.bisect_left(adps, x)
        x0, x1 = adps[j - 1], adps[j]; y0, y1 = projs[j - 1], projs[j]
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y0

    n = 0
    for r in rows:
        if r.get("proj") is None and r.get("adp") is not None:
            ad, pj = anchors.get(r["pos"], (None, None))
            val = interp(ad, pj, float(r["adp"])) if ad else interp(g_adps, g_projs, float(r["adp"]))
            if val is not None:
                r["proj"] = round(float(val), 2); r["proj_src"] = "adp_curve"; n += 1
    return n


def _read_ceiling() -> dict:
    """ceiling_p95 per player. Prefer layer2_player_params.csv; if it lacks p95 (it does in this
    repo — it only has params), fall back to player_sim_distributions.csv's `p95` column."""
    # Try layer2 first (per contract ordering).
    l2 = _pipe("layer2_player_params.csv")
    if os.path.exists(l2):
        df = pd.read_csv(l2)
        if "p95" in df.columns:
            return {_norm(nm): v for nm, v in zip(df["name"], df["p95"])}
    # Fallback: simulated distribution p95 (this is the real source in this repo).
    sd = _pipe("player_sim_distributions.csv")
    if os.path.exists(sd):
        df = pd.read_csv(sd)
        if "p95" in df.columns:
            out = {}
            for nm, v in zip(df["name"], df["p95"]):
                out.setdefault(_norm(nm), v)
            return out
    return {}


def _read_byes() -> dict:
    """byes_2026.json -> {TEAM: bye_week}."""
    return json.load(open(_pipe("byes_2026.json"), encoding="utf-8"))


def _read_playoff_overlay() -> dict:
    """engine/playoff_overlay.csv (Agent B) -> {norm_name: playoff_up}. Default empty if absent."""
    path = _repo("engine", "playoff_overlay.csv")
    if not os.path.exists(path):
        return {}
    try:
        df = pd.read_csv(path)
    except Exception:
        return {}
    if "playoff_up" not in df.columns or "name" not in df.columns:
        return {}
    return {_norm(nm): v for nm, v in zip(df["name"], df["playoff_up"])}


def _apply_flag_nudge(rows: list) -> int:
    """Optional ADP-anchored flag nudge. If flag_ranks.json exists, move each flagged player's `rank`
    by his bounded flag nudge (+/- a few spots; strong boom/skill flags -> earlier, weak -> later).
    Market ADP is left untouched; the original rank is preserved as `mkt_rank`. Missing file -> no-op.
    Never raises, so an absent or malformed file can never break a draft grade."""
    try:
        path = _repo("flag_ranks.json")
        if not os.path.exists(path):
            return 0
        fr = json.load(open(path, encoding="utf-8")).get("players", {})
        n = 0
        for r in rows:
            f = fr.get(_norm(r["name"]))
            r["mkt_rank"] = r["rank"]
            nud = int(round(float(f["nudge"]))) if (f and f.get("nudge") is not None) else 0
            r["flag_nudge"] = nud
            if nud:
                n += 1
        if not n:
            return 0
        # Re-rank contiguously by (market rank + nudge); original rank breaks ties. Board ranks are
        # already contiguous 1..N, so this is scale-preserving: each player lands ~his own rank +/- a
        # few spots, with no collisions or underflow.
        for i, r in enumerate(sorted(rows, key=lambda z: (z["mkt_rank"] + z["flag_nudge"], z["mkt_rank"])), 1):
            r["rank"] = i
        return n
    except Exception:
        return 0


def load_board() -> list[dict]:
    """Return every draftable player as a dict.

    Schema (per Contract 1, plus sim_name):
        {name, sim_name, pos, team, adp, rank, proj, ceiling_p95, bye, playoff_up}

    Sources:
      - merged_rankings_upload.csv : name, pos, team, rank (file order), adp (partial)
      - dk_adp.csv                 : canonical DK adp (fills/overrides where present)
      - clay_2026.csv              : proj (dk_pg)
      - player_sim_distributions.csv / layer2_player_params.csv : ceiling_p95 (p95)
      - byes_2026.json             : bye (by team)
      - engine/playoff_overlay.csv : playoff_up (else 0.0)

    proj / ceiling_p95 / playoff_up are resolved through canon() so a board name that is a
    first-name variant of the Clay name (e.g. "Kenneth Walker III") still picks up its projection
    and becomes gradeable. sim_name carries the resolved Clay/sim name (None if unresolved).
    """
    merged = _read_merged_rankings()
    dk = _read_dk_adp()
    proj = _read_proj(os.environ.get("BB_PLATFORM", "DK"))
    ceil = _read_ceiling()
    byes = _read_byes()
    overlay = _read_playoff_overlay()

    df = merged.merge(dk, on="key", how="outer")

    # Names/pos/team: prefer merged-ranking record, fall back to dk_adp record.
    df["name"] = df["name"].fillna(df["name_dk"])
    df["pos"] = df["pos"].fillna(df["pos_dk"])
    df["team"] = df["team"].fillna(df["team_dk"])
    # ADP: prefer DK adp (canonical draft adp), fall back to merged-file adp.
    df["adp"] = df["adp_dk"].fillna(df["adp"])

    # Players that exist only in dk_adp (not in merged) get a rank after the merged tail,
    # ordered by their ADP so the board stays monotonic-ish.
    max_rank = int(df["rank"].max()) if df["rank"].notna().any() else 0
    missing = df["rank"].isna()
    if missing.any():
        order = df.loc[missing, "adp"].rank(method="first")
        df.loc[missing, "rank"] = max_rank + order

    df = df.dropna(subset=["name", "pos", "team"]).copy()
    df["key"] = df["name"].map(_norm)
    df = df.drop_duplicates(subset="key", keep="first")

    out = []
    for _, r in df.sort_values("rank").iterrows():
        k = r["key"]
        nm = str(r["name"])
        pos = str(r["pos"])
        # Resolve the Clay/sim canonical name (recovers first-name variants like
        # "Kenneth Walker III" -> "Ken Walker III"); fall back to the board key when unresolved
        # (exact-matched players are unchanged). proj/ceiling/playoff_up are all keyed on the
        # NORMALIZED Clay name, so a recovered player now shows a projection and is gradeable.
        sim_name = canon(nm, pos)
        lk = _norm(sim_name) if sim_name else k
        out.append({
            "name": nm,
            "sim_name": sim_name,
            "pos": pos,
            "team": str(r["team"]),
            "adp": (float(r["adp"]) if pd.notna(r["adp"]) else None),
            "rank": int(r["rank"]),
            "proj": (float(proj[lk]) if lk in proj and pd.notna(proj[lk]) else None),
            "ceiling_p95": (float(ceil[lk]) if lk in ceil and pd.notna(ceil[lk]) else None),
            "bye": (int(byes[r["team"]]) if r["team"] in byes else None),
            "playoff_up": (float(overlay[lk]) if lk in overlay and pd.notna(overlay[lk]) else 0.0),
            "proj_src": ("clay" if (lk in proj and pd.notna(proj[lk])) else None),
        })
    # close the projection-coverage hole so no draftable star is silently ungradeable
    _impute_missing_proj(out)
    _apply_flag_nudge(out)   # ADP-anchored flag nudge (no-op if flag_ranks.json absent)
    return out


# ===========================================================================
# grade
# ===========================================================================
def _canon_rosters(rosters: dict) -> dict:
    """Remap every player name in a {team:[names]} dict from its board name to its Clay/sim
    canonical name via canon(), so survival_chain / win_delta resolve it. Names that canon can't
    resolve are left AS-IS (the sim skips them, exactly as before). Names that already matched are
    returned unchanged by canon (exact-match path), so this is a no-op for them -> no regression.
    """
    out = {}
    for team, names in rosters.items():
        out[team] = [(canon(n) or n) for n in names]
    return out


def grade(rosters: dict, me: str = "rsbathla") -> dict:
    """Grade `me` against the field via survival_chain.chain.

    Returns: {p_adv, surv_W15, surv_W16, win_W17, title_share, anchor}
    where anchor is the W17 anchor game string with piece count, e.g. "BAL@CIN(3)".

    Mirrors survival_chain.chain numbers exactly (same model, same seed). The pipeline uses
    relative paths, so the call is wrapped in cwd->pipeline/.
    """
    sc, _ = _load_engine_modules()
    # Remap board names -> Clay names so recovered players (e.g. "Kenneth Walker III" ->
    # "Ken Walker III") are resolved by the sim instead of silently dropped. Already-matched names
    # are returned unchanged by canon, so this reproduces survival_chain exactly for them.
    rosters = _canon_rosters(rosters)
    with _in_pipeline():
        df = sc.chain(rosters, me)
    row = df[df["team"] == me]
    if len(row) == 0:
        raise KeyError(f"team {me!r} not found in rosters {list(rosters)}")
    r = row.iloc[0]
    anchor = f"{r['W17_anchor']}({int(r['anchor_pieces'])})"
    return {
        "p_adv": float(r["p_adv"]),
        "surv_W15": float(r["surv_W15"]),
        "surv_W16": float(r["surv_W16"]),
        "win_W17": float(r["win_W17"]),
        "title_share": float(r["title_share"]),
        "anchor": anchor,
    }


# ===========================================================================
# pick_values
# ===========================================================================
def pick_values(rosters: dict, me: str, candidates: list[str], ns: int = 1500) -> dict:
    """Marginal value of each candidate added to `me`'s roster, via win_delta.win_deltas.

    Returns: {name: {dadv, dtitle, dw17}} (percentage-point deltas vs the current roster).
    Uses common random numbers (baseline + each candidate share the same sim) for clean deltas.
    """
    _, wd = _load_engine_modules()
    # Remap board names -> Clay names for BOTH the field rosters and the candidates so win_delta
    # resolves recovered players. Track each requested candidate's canonical form so we can re-key
    # the results back to the caller's original candidate strings.
    rosters = _canon_rosters(rosters)
    cand_canon = {c: (canon(c) or c) for c in candidates}
    with _in_pipeline():
        _base, deltas = wd.win_deltas(rosters, me, list(cand_canon.values()), ns=ns)
    # Re-key to the requested order; win_deltas keys by the (canonical) candidate name as passed in.
    out = {}
    for c in candidates:
        d = deltas.get(cand_canon[c], {"dtitle": 0.0, "dadv": 0.0, "dw17": 0.0})
        out[c] = {"dadv": d["dadv"], "dtitle": d["dtitle"], "dw17": d["dw17"]}
    return out


# ===========================================================================
# parse_board
# ===========================================================================
# Board-name resolver, reusing draft_assistant.py's KEY-table approach but seeded from load_board()
# (so it resolves against the full draftable universe, live names + ADP-resolved pos/team picks).
_BOARD_KEYS = None     # {norm_name: display_name}
_BOARD_DF = None       # DataFrame[name,pos,team,adp,key]


def _board_index():
    """Build (and cache) the name resolver + ADP table from load_board()."""
    global _BOARD_KEYS, _BOARD_DF
    if _BOARD_KEYS is not None:
        return _BOARD_KEYS, _BOARD_DF
    board = load_board()
    _BOARD_DF = pd.DataFrame(board)
    _BOARD_DF["key"] = _BOARD_DF["name"].map(_norm)
    _BOARD_KEYS = {}
    for nm in _BOARD_DF["name"]:
        _BOARD_KEYS.setdefault(_norm(nm), nm)
    return _BOARD_KEYS, _BOARD_DF


def _resolve_name(x: str) -> str | None:
    """Resolve a raw board token to a canonical display name (exact key, else substring match)."""
    keys, _ = _board_index()
    k = _norm(x)
    if not k:
        return None
    if k in keys:
        return keys[k]
    cands = [kk for kk in keys if k in kk or kk in k]
    if cands:
        return keys[cands[0]]
    return None


def _ov_for(seat: int, rnd: int, teams: int = 12) -> int:
    """Overall pick number for (seat, round) in a snake draft (matches draft_pick.ov_for)."""
    return (rnd - 1) * teams + (seat if rnd % 2 == 1 else teams + 1 - seat)


def parse_board(text: str, seat, teams: int = 12, rounds: int = 20) -> dict:
    """Parse a pasted DK draft board into draft state.

    Handles BOTH board layouts (logic ported from draft_pick.py):
      1. LIVE DK in-draft board with player names present.
      2. Pre-draft / partial board showing only round.pick, overall, POS, TEAM -> resolved to a
         player via ADP (closest ADP among un-taken players of that pos+team).

    `seat` may be an int seat number (1..teams) or a username string (matched against the board
    column headers, e.g. "rsbathla").

    Returns:
      {pick:int, round:int, seat:int, my_roster:[names], counts:{QB,RB,WR,TE}, available:[names]}
        - pick   : our next overall pick number
        - round  : the round that pick falls in
        - my_roster : canonical player names we've drafted so far
        - counts : positional counts of my_roster
        - available : draftable player names still on the board (full universe minus everyone gone)
    """
    keys, board_df = _board_index()

    # Normalize line endings; de-RTF if needed (mirrors draft_pick.py).
    txt = str(text).replace("\r\n", "\n").replace("\r", "\n")
    if txt.lstrip().startswith("{\\rtf"):
        try:
            from striprtf.striprtf import rtf_to_text
            txt = rtf_to_text(txt)
        except Exception:
            txt = re.sub(r"\\par[d]?|\\line", "\n", txt)
            txt = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", txt)
            txt = re.sub(r"[{}]", "", txt)

    # Seat column headers, e.g. "rsbathla\nQB\n#\nRB\n#\nWR\n#\nTE\n#".
    heads = re.findall(
        r"\n([A-Za-z0-9_\.]+)\s*\nQB\s*\n\d+\s*\nRB\s*\n\d+\s*\nWR\s*\n\d+\s*\nTE\s*\n\d+", txt
    )
    if isinstance(seat, int) or (isinstance(seat, str) and seat.isdigit()):
        seat_n = int(seat)
    elif seat in heads:
        seat_n = heads.index(seat) + 1
    else:
        seat_n = next((i + 1 for i, h in enumerate(heads) if str(seat).lower() in h.lower()), None)
    if seat_n is None:
        raise ValueError(f"could not find seat {seat!r} in board headers {heads}")

    # ---- Layout 1: live named board ----
    named = re.findall(
        r"(\d+)\.(\d+)\s*\n\s*(\d+)\s*\n\s*(.+?)\s*icon\s*\n\s*(QB|RB|WR|TE)\s*\n\s*([A-Z]{2,3})\s*\n\s*\(BYE",
        txt,
    )
    gone = []          # canonical names, drafted (any team)
    bypick = {}        # overall pick number -> canonical name
    if named:
        for _rnd, _inr, ov, name, _pos, _team in named:
            cn = _resolve_name(name) or name.strip()
            gone.append(cn)
            bypick[int(ov)] = cn
    else:
        # ---- Layout 2: pos/team only -> resolve via ADP ----
        picks = sorted(set(
            (int(o), p, t)
            for _, _, o, p, t in re.findall(
                r"(\d+)\.(\d+)\s*\n\s*(\d+)\s*\n\s*(QB|RB|WR|TE)\s*\n\s*([A-Z]{2,3})", txt
            )
        ))
        adp = board_df.dropna(subset=["adp"]).copy()
        adp["team"] = adp["team"].replace({"LA": "LAR"})
        taken = set()
        for ov, pos, team in picks:
            c = adp[(adp.pos == pos) & (adp.team == team) & (~adp.name.isin(taken))]
            if len(c):
                nm = c.assign(d=(c.adp - ov).abs()).sort_values("d").iloc[0]["name"]
                taken.add(nm)
                gone.append(nm)
                bypick[ov] = nm

    # Our picks: snake-order overall numbers for our seat.
    my_ov = {_ov_for(seat_n, r, teams) for r in range(1, rounds + 1)}
    my_roster = [bypick[o] for o in sorted(my_ov) if o in bypick]

    # Next pick = our lowest snake slot not yet filled (else just past the last pick seen).
    open_slots = [o for o in sorted(my_ov) if o not in bypick]
    next_pick = open_slots[0] if open_slots else (max(bypick) + 1 if bypick else 1)
    rnd = (next_pick - 1) // teams + 1

    # Positional counts of my roster.
    pos_by_key = dict(zip(board_df["key"], board_df["pos"]))
    counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
    for nm in my_roster:
        p = pos_by_key.get(_norm(nm))
        if p in counts:
            counts[p] += 1

    # Available = full draftable universe minus everyone gone.
    gone_keys = {_norm(g) for g in gone}
    available = [nm for nm in board_df["name"] if _norm(nm) not in gone_keys]

    return {
        "pick": int(next_pick),
        "round": int(rnd),
        "seat": int(seat_n),
        "my_roster": my_roster,
        "counts": counts,
        "available": available,
    }


__all__ = ["load_board", "grade", "pick_values", "parse_board", "canon"]


if __name__ == "__main__":
    # Tiny self-check when run directly.
    b = load_board()
    print(f"load_board -> {len(b)} players; sample[0]={b[0]}")
