"""Smoke test for engine/bbengine.py (Contract 1).

Run from anywhere:
    python engine/test_bbengine.py            (from bestball/ root)
    python test_bbengine.py                   (from engine/)

Verifies:
  1. load_board(): >300 players, all schema fields present.
  2. A mock 12-team, 18-round snake draft built from ADP.
  3. grade() returns sane values (0<=p_adv<=1, title_share>0) AND reproduces
     survival_chain.chain() exactly for the same roster (spot-check).
  4. pick_values() on 3 real candidates returns dtitle/dadv/dw17.
  5. parse_board() on a small synthetic board returns a plausible state.

Sims are kept fast: survival_chain.NS is forced low (1000).
"""
import os
import sys

# Make bbengine importable no matter where this is launched from.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bbengine as bb


REQUIRED_FIELDS = {"name", "pos", "team", "adp", "rank", "proj", "ceiling_p95", "bye", "playoff_up"}
ME = "rsbathla"


def _build_snake_draft(board, teams=12, rounds=18, me=ME):
    """Build a plausible 12-team x 18-round snake draft by walking ADP order.

    Returns rosters: {team_name: [player names]} with `me` at seat 10 (matches the live board's
    rsbathla seat), so grade()/pick_values() have a realistic 'me' roster and a full field.
    """
    # Draftable pool with a usable ADP, ordered by ADP (best first).
    pool = [p for p in board if p["adp"] is not None]
    pool = sorted(pool, key=lambda p: p["adp"])

    seats = list(range(1, teams + 1))
    team_names = {s: (me if s == 10 else f"team{s:02d}") for s in seats}
    rosters = {team_names[s]: [] for s in seats}

    pi = 0
    for rnd in range(1, rounds + 1):
        seat_order = seats if rnd % 2 == 1 else list(reversed(seats))
        for s in seat_order:
            if pi >= len(pool):
                break
            rosters[team_names[s]].append(pool[pi]["name"])
            pi += 1
    return rosters, team_names


def test_load_board():
    board = bb.load_board()
    assert isinstance(board, list), "load_board must return a list"
    assert len(board) > 300, f"expected >300 players, got {len(board)}"
    for p in board[:50]:
        assert REQUIRED_FIELDS <= set(p.keys()), f"missing fields: {REQUIRED_FIELDS - set(p)}"
    # Spot-check the top player has core data.
    top = board[0]
    assert top["name"] and top["pos"] and top["team"], "top player missing name/pos/team"
    n_proj = sum(1 for p in board if p["proj"] is not None)
    n_ceil = sum(1 for p in board if p["ceiling_p95"] is not None)
    n_bye = sum(1 for p in board if p["bye"] is not None)
    print(f"  [1] load_board: {len(board)} players | rank#1={top['name']} ({top['pos']} {top['team']}, "
          f"adp={top['adp']:.1f}) | proj on {n_proj} | ceiling_p95 on {n_ceil} | bye on {n_bye}")
    return board


def test_grade_and_reproduce(rosters):
    """grade() sane + reproduces survival_chain.chain() numbers for the same roster."""
    g = bb.grade(rosters, me=ME)
    assert 0.0 <= g["p_adv"] <= 1.0, f"p_adv out of range: {g['p_adv']}"
    assert 0.0 <= g["surv_W15"] <= 1.0, f"surv_W15 out of range: {g['surv_W15']}"
    assert 0.0 <= g["surv_W16"] <= 1.0, f"surv_W16 out of range: {g['surv_W16']}"
    assert 0.0 <= g["win_W17"] <= 1.0, f"win_W17 out of range: {g['win_W17']}"
    assert g["title_share"] > 0.0, f"title_share must be >0, got {g['title_share']}"
    assert isinstance(g["anchor"], str) and g["anchor"], "anchor must be a non-empty string"
    print(f"  [3] grade({ME}): p_adv={g['p_adv']:.3f} W15={g['surv_W15']:.3f} W16={g['surv_W16']:.3f} "
          f"W17={g['win_W17']:.3f} title_share={g['title_share']:.4f} anchor={g['anchor']}")

    # --- reproduce survival_chain.chain() directly (same model, same seed, same NS) ---
    # grade() now routes roster names through the canon() chokepoint (board-name -> Clay/sim name)
    # so first-name variants like "Kenneth Walker III" resolve instead of being silently dropped.
    # To prove grade() is still a faithful wrapper of survival_chain.chain(), compare against chain()
    # run on the SAME canon-resolved rosters (canon is a no-op for already-matched names, so this is
    # identical to the old check for those — it only additionally resolves the recoverable names).
    sc, _ = bb._load_engine_modules()
    import copy
    with bb._in_pipeline():
        df = sc.chain(bb._canon_rosters(copy.deepcopy(rosters)), ME)
    r = df[df["team"] == ME].iloc[0]
    pairs = [
        ("p_adv", g["p_adv"], float(r["p_adv"])),
        ("surv_W15", g["surv_W15"], float(r["surv_W15"])),
        ("surv_W16", g["surv_W16"], float(r["surv_W16"])),
        ("win_W17", g["win_W17"], float(r["win_W17"])),
        ("title_share", g["title_share"], float(r["title_share"])),
    ]
    for name, a, b in pairs:
        assert abs(a - b) < 1e-9, f"grade() != chain() for {name}: {a} vs {b}"
    print(f"  [3b] grade() reproduces survival_chain.chain() exactly "
          f"(p_adv {g['p_adv']:.6f}=={float(r['p_adv']):.6f}, "
          f"title_share {g['title_share']:.6f}=={float(r['title_share']):.6f})")
    return g


def test_pick_values(rosters, board):
    """pick_values() on 3 real, currently-undrafted candidates returns the three deltas."""
    drafted = {bb._norm(n) for names in rosters.values() for n in names}
    # Prefer candidates that are in the sim universe (have proj) so deltas are meaningful.
    cands = []
    for p in board:
        if p["proj"] is None:
            continue
        if bb._norm(p["name"]) in drafted:
            continue
        cands.append(p["name"])
        if len(cands) == 3:
            break
    assert len(cands) == 3, f"could not find 3 undrafted candidates, got {cands}"

    pv = bb.pick_values(rosters, ME, cands, ns=1000)
    assert set(pv.keys()) == set(cands), f"pick_values keys mismatch: {pv.keys()} vs {cands}"
    for c in cands:
        d = pv[c]
        assert set(d.keys()) == {"dadv", "dtitle", "dw17"}, f"missing delta keys for {c}: {d.keys()}"
        for k, v in d.items():
            assert isinstance(v, (int, float)), f"{c}.{k} not numeric: {v!r}"
    print("  [4] pick_values (3 candidates):")
    for c in cands:
        d = pv[c]
        print(f"        {c:24s} dTitle={d['dtitle']:+6.2f}  dAdv={d['dadv']:+5.1f}  dW17={d['dw17']:+5.1f}")
    return pv


def test_parse_board(board):
    """parse_board() on a small synthetic NAMED board (first few real players, snake order)."""
    # Take the 6 highest-ADP players to seed a 12-team board's first 6 picks (round 1, seats 1..6).
    pool = sorted([p for p in board if p["adp"] is not None], key=lambda p: p["adp"])[:6]
    teams = 12
    lines = ["\n"]  # header block: 12 seat columns, rsbathla at seat 10
    seat_names = [f"user{i}" if i != 10 else "rsbathla" for i in range(1, teams + 1)]
    for nm in seat_names:
        lines.append(f"{nm}\nQB\n0\nRB\n0\nWR\n0\nTE\n0\n")
    # 6 named picks, round 1, overall 1..6, in DK's "name icon\nPOS\nTEAM\n(BYE..." shape.
    for i, p in enumerate(pool, start=1):
        lines.append(f"1.{i}\n{i}\n{p['name']} icon\n{p['pos']}\n{p['team']}\n(BYE 14)\n")
    synthetic = "\n".join(lines)

    st = bb.parse_board(synthetic, "rsbathla", teams=teams)
    assert set(st.keys()) == {"pick", "round", "seat", "my_roster", "counts", "available"}, \
        f"parse_board keys: {st.keys()}"
    assert st["seat"] == 10, f"expected seat 10 for rsbathla, got {st['seat']}"
    # 6 picks made (overall 1..6); rsbathla (seat 10) hasn't picked -> next pick is overall 10, round 1.
    assert st["pick"] == 10, f"expected next pick=10, got {st['pick']}"
    assert st["round"] == 1, f"expected round 1, got {st['round']}"
    assert st["my_roster"] == [], f"rsbathla should have no picks yet, got {st['my_roster']}"
    # 6 players gone -> available is the rest of the universe.
    assert len(st["available"]) == len(board) - 6, \
        f"available should be {len(board) - 6}, got {len(st['available'])}"
    assert set(st["counts"]) == {"QB", "RB", "WR", "TE"}, f"counts keys: {st['counts']}"
    print(f"  [5] parse_board (synthetic, 6 picks): seat={st['seat']} next_pick={st['pick']} "
          f"round={st['round']} my_roster={st['my_roster']} counts={st['counts']} "
          f"available={len(st['available'])}")

    # Also exercise the ADP-resolution path (pos/team-only board, no names).
    lines2 = ["\n"]
    for nm in seat_names:
        lines2.append(f"{nm}\nQB\n0\nRB\n0\nWR\n0\nTE\n0\n")
    for i, p in enumerate(pool, start=1):
        lines2.append(f"1.{i}\n{i}\n{p['pos']}\n{p['team']}\n")
    synthetic2 = "\n".join(lines2)
    st2 = bb.parse_board(synthetic2, "rsbathla", teams=teams)
    assert st2["seat"] == 10 and st2["pick"] == 10, f"ADP-path state off: {st2['pick']}/{st2['seat']}"
    assert len(st2["available"]) == len(board) - len(pool), \
        f"ADP-path available {len(st2['available'])} != {len(board) - len(pool)}"
    print(f"  [5b] parse_board (ADP-resolved pos/team board): next_pick={st2['pick']} "
          f"resolved {len(pool)} picks, available={len(st2['available'])}")
    return st


def main():
    # Keep sims fast.
    sc, _ = bb._load_engine_modules()
    sc.NS = 1000
    print(f"survival_chain.NS set to {sc.NS} for fast sims")
    print(f"cwd at test start: {os.getcwd()} (engine must work from here)")

    board = test_load_board()
    rosters, team_names = _build_snake_draft(board)
    rsize = len(rosters[ME])
    assert rsize == 18, f"mock draft should give {ME} 18 picks, got {rsize}"
    print(f"  [2] mock 12-team x 18-round snake draft: {len(rosters)} teams, "
          f"{ME} has {rsize} players (e.g. {rosters[ME][:3]} ...)")

    test_grade_and_reproduce(rosters)
    test_pick_values(rosters, board)
    test_parse_board(board)

    print("\nPASS")


if __name__ == "__main__":
    main()
