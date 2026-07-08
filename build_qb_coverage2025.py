#!/usr/bin/env python3
"""build_qb_coverage2025.py — QB passing stats BY COVERAGE SCHEME (2025) into
boom/qb_coverage_2025.json, for the warroom QB dossier's "Vs coverage (passing)" table.

Source: NFL-master/FP_SWEEP/2025/Passing/coverageScheme/qb_coverage_pull_2025.json —
FantasyPoints Advanced Passing, 2025 season, DraftKings scoring, pulled per coverage
shell via the authenticated /values endpoint (see FP_SWEEP_CATALOG.md; the auth-header
replay is what unlocks the full set vs the 5-row free preview).

Output: {fn(name): {"pos":"QB", "schemes": {<scheme>: {db,cmp,ypa,td,intc,rate,adot,dk,
  rate_pctl}}}} — rate_pctl is the passer-rating percentile vs the QB pool WITHIN that
scheme (min DB gate), so the renderer can tint elite/weak the same way the WR tables do.

Fail-loud: refuses to write on an empty/degenerate pull (the empty-write class, per the
repo's data-loss guards). Wire: run_all.py after build_coverage_adv2025.py.
"""
import json, os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "NFL-master/FP_SWEEP/2025/Passing/coverageScheme/qb_coverage_pull_2025.json")
OUT = os.path.join(HERE, "boom/qb_coverage_2025.json")
# the 7 real coverage shells (situational Red Zone/Goal Line/Prevent/Bracket/Misc are banked
# in the raw but not rendered — they are not "how he plays vs a coverage shell")
SHELLS = ["Cover 0", "Cover 1", "Cover 2", "Cover 2 Man", "Cover 3", "Cover 4", "Cover 6"]
MIN_DB = 10          # a QB needs >=10 dropbacks vs a shell to be ranked in it
MIN_QBS = 20         # pool-sanity: fewer than this in the common shells = broken pull


def fn(n):
    n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    return n.replace(".", "").replace("'", "").replace("-", " ")


def pctl(vals, x):
    """percentile of x within vals (0-100), midrank; vals non-empty."""
    if x is None or not vals:
        return None
    below = sum(1 for v in vals if v < x); eq = sum(1 for v in vals if v == x)
    return round(100.0 * (below + 0.5 * eq) / len(vals))


def main():
    if not os.path.exists(SRC):
        print(f"FATAL: raw pull not found at {SRC}"); return 1
    raw = json.load(open(SRC))
    # gate: the common shells must be populated
    common = [len(raw.get(s, [])) for s in ("Cover 1", "Cover 3", "Cover 4")]
    if min(common) < MIN_QBS:
        print(f"FATAL: common shells underpopulated {common} (<{MIN_QBS}) — refusing to overwrite {OUT}"); return 1

    # per shell: collect rating pool over QBs meeting MIN_DB, for percentile tinting
    pools = {}
    for s in SHELLS:
        rs = [r["rate"] for r in raw.get(s, []) if (r.get("db") or 0) >= MIN_DB and r.get("rate") is not None]
        pools[s] = rs

    players = {}
    for s in SHELLS:
        for r in raw.get(s, []):
            if (r.get("db") or 0) < MIN_DB:
                continue
            k = fn(r["n"])
            p = players.setdefault(k, {"pos": "QB", "name": r["n"], "schemes": {}})
            p["schemes"][s] = {
                "db": r.get("db"), "cmp": r.get("cmp"), "ypa": r.get("ypa"),
                "td": r.get("td"), "intc": r.get("intc"), "rate": r.get("rate"),
                "adot": r.get("adot"), "dk": r.get("dk"),
                "rate_pctl": pctl(pools[s], r.get("rate")),
            }
    if len(players) < MIN_QBS:
        print(f"FATAL: only {len(players)} QBs built (<{MIN_QBS}) — refusing to overwrite {OUT}"); return 1

    json.dump(players, open(OUT, "w"), ensure_ascii=False, indent=0)
    per = {s: len(pools[s]) for s in SHELLS}
    print(f"wrote {os.path.relpath(OUT, HERE)}: {len(players)} QBs · per-shell ranked {per}")
    a = players.get("josh allen", {}).get("schemes", {})
    if a:
        print("  Josh Allen sanity —",
              " · ".join(f"{s.split()[-1]}:{a[s]['rate']}({a[s]['rate_pctl']}pct)" for s in SHELLS if s in a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
