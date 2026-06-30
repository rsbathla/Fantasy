"""Verification harness for engine/decision_tree.py (Contract 4).

Builds a realistic mid-draft state (mock 12-team ADP snake, rsbathla drafted through ~R4),
runs build_tree, validates the output against engine/tree_schema.json (Draft7Validator),
prints the tree indented, spot-checks that branch deltas came from pick_values (not all zeros),
reports runtime, and writes engine/sample_tree.json for the dashboard.

Run:  python engine/verify_decision_tree.py   (or from engine/: python verify_decision_tree.py)
Note: a fresh PYTHONPYCACHEPREFIX is recommended if iterating on the module under a mounted FS.
"""
import os
import sys
import json
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bbengine as bb
import decision_tree as dt

ME = "rsbathla"
SEAT = 7
TEAMS = 12
THROUGH_ROUND = 4


def build_snake_through(board, seat=SEAT, teams=TEAMS, through_round=THROUGH_ROUND, me=ME):
    """Walk ADP order to fill a snake draft through `through_round`, with `me` at `seat`."""
    pool = sorted([p for p in board if p["adp"] is not None], key=lambda p: p["adp"])
    seats = list(range(1, teams + 1))
    names = {s: (me if s == seat else f"team{s:02d}") for s in seats}
    rosters = {names[s]: [] for s in seats}
    pi = 0
    for rnd in range(1, through_round + 1):
        order = seats if rnd % 2 == 1 else list(reversed(seats))
        for s in order:
            if pi >= len(pool):
                break
            rosters[names[s]].append(pool[pi]["name"])
            pi += 1
    return rosters


def indent_tree(node, depth=0, lines=None):
    if lines is None:
        lines = []
    pad = "  " * depth
    lines.append(f"{pad}{node['label']}")
    for br in node["branches"]:
        team = br.get("team", "")
        lines.append(f"{pad}  - [{br['cond']}]")
        lines.append(f"{pad}      TAKE {br['take']} ({br['pos']} {team})  "
                     f"dTitle={br['dTitle']:+.3f} dAdv={br['dAdv']:+.3f} dW17={br['dW17']:+.3f} "
                     f"playoff_up={br.get('playoff_up', 0):.2f}")
        lines.append(f"{pad}      why: {br['reason']}")
        if "then" in br:
            indent_tree(br["then"], depth + 3, lines)
    return lines


def collect_deltas(node, acc=None):
    if acc is None:
        acc = []
    for br in node["branches"]:
        acc.append((br["dTitle"], br["dAdv"], br["dW17"]))
        if "then" in br:
            collect_deltas(br["then"], acc)
    return acc


def main():
    t = time.time()
    board = bb.load_board()
    print(f"load_board: {len(board)} players in {time.time()-t:.2f}s")

    rosters = build_snake_through(board)
    my = rosters[ME]
    bidx = {bb._norm(p['name']): p for p in board}
    print(f"mock snake through R{THROUGH_ROUND}: {ME} (seat {SEAT}) has {len(my)} picks:")
    for nm in my:
        p = bidx.get(bb._norm(nm), {})
        print(f"    {nm:24s} {p.get('pos','?')} {p.get('team','?')}  ADP {p.get('adp')}")

    t0 = time.time()
    tree = dt.build_tree(board, rosters, me=ME, seat=SEAT, plies=2)
    runtime = time.time() - t0
    print(f"\nbuild_tree(plies=2) runtime: {runtime:.1f}s\n")

    schema = json.load(open(os.path.join(_HERE, "tree_schema.json")))
    from jsonschema import Draft7Validator
    errs = sorted(Draft7Validator(schema).iter_errors(tree), key=lambda e: list(e.path))
    if errs:
        print("SCHEMA ERRORS:")
        for e in errs:
            print(f"  - {list(e.path)}: {e.message}")
        raise SystemExit(1)
    print("schema OK")

    deltas = collect_deltas(tree["tree"])
    nonzero = sum(1 for (a, b, c) in deltas if abs(a) + abs(b) + abs(c) > 0)
    print(f"delta spot-check: {nonzero}/{len(deltas)} branch picks have a non-zero sim delta")
    assert nonzero >= max(1, len(deltas) // 2), "too many zero deltas - pick_values not wired?"

    h, s = tree["headline"], tree["state"]
    print(f"\nSTATE: pick {s['pick']} (R{s['round']}), seat {s['seat']}, counts {s['counts']}, "
          f"anchor {s['anchor']}")
    print(f"HEADLINE: take {h['take']}  dTitle={h['dTitle']:+.3f} dAdv={h['dAdv']:+.3f}")
    print(f"   why: {h['why']}")

    print("\n===== DECISION TREE =====")
    for ln in indent_tree(tree["tree"]):
        print(ln)

    out = os.path.join(_HERE, "sample_tree.json")
    json.dump(tree, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
