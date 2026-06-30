"""Property + parity tests for the shared core and layers — the test layer the audit found
missing (fn/percentile/fusion/flags had ZERO tests).

Run:  python3 bbdfs/tests/test_core.py        (no pytest needed)
  or: cd bbdfs && python3 -m pytest tests -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402

import bbdfs  # noqa: E402,F401
from bbdfs import core  # noqa: E402
from bbdfs.flags import FlagSpec, build_position, SKILL, MATCHUP  # noqa: E402


# ---- names / teams / parse (dedupe targets) ----
def test_fn_normalizes():
    assert core.fn("A.J. Brown Jr.") == "aj brown"
    assert core.fn("Amon-Ra St. Brown") == "amon ra st brown"


def test_team_code():
    assert core.team_code("Las Vegas Raiders") == "LV"
    assert core.team_code("Raiders") == "LV"
    assert core.team_code("LA") == "LAR"


def test_parse():
    assert core.num('"1,234"') == 1234.0
    assert core.pct("43.5%") == 43.5
    assert core.pnum("97%Elite") == 97.0
    assert core.ab("1PIT") == "PIT"


# ---- statlib percentile policy ----
def test_pctl_abstains_and_bounds():
    raw = pd.Series([1, 2, 3, None, 5])
    pos = pd.Series(["WR"] * 5)
    p = core.pctl(raw, pos)
    assert p.isna().sum() == 1                      # missing ABSTAINS, never becomes 50
    assert p.dropna().between(0, 100).all()


def test_pctl_neutral_fill_is_opt_in():
    raw = pd.Series([1, 2, None])
    pos = pd.Series(["WR"] * 3)
    assert core.pctl(raw, pos, fill=50).iloc[2] == 50.0


def test_pctl_is_within_position():
    raw = pd.Series([10, 20, 100, 200])
    pos = pd.Series(["WR", "WR", "RB", "RB"])
    p = core.pctl(raw, pos)
    # top of each position cohort should rank near the top regardless of raw scale
    assert p.iloc[1] > 50 and p.iloc[3] > 50


# ---- fusionkit ----
def test_fuse_single_vote_zero_divergence():
    pos = pd.Series(["WR", "WR", "WR"])
    ss = core.SourceSet(pos)
    ss.add("a", [90, 50, 10])
    ss.add("b", [80, None, 20])
    b = core.fuse_board(ss)
    assert b["n_votes"].iloc[1] == 1               # one source abstained
    assert b["divergence"].iloc[1] == 0.0          # single vote -> divergence 0
    assert 0 <= b["consensus"].dropna().min() <= b["consensus"].dropna().max() <= 100


def test_leverage_flags_shape():
    pos = pd.Series(["WR", "WR"])
    ss = core.SourceSet(pos)
    ss.add("a", [99, 1])
    ss.add("b", [98, 2])
    tags = core.leverage_flags(core.fuse_board(ss))
    assert isinstance(tags, list) and len(tags) == 2


# ---- playoff_week ----
def test_playoff_monotonic_in_env():
    lo = core.p_ceiling(18, 0.5, 22, env=0.9)
    hi = core.p_ceiling(18, 0.5, 22, env=1.2)
    assert 0 <= lo < hi <= 1


def test_playoff_up_weights_sum_to_one():
    assert core.playoff_up(1, 1, 1) == 1.0


# ---- flag engine (config-driven) ----
def test_flag_engine_lights_and_grades():
    specs = [
        FlagSpec("ALPHA", SKILL, lambda c: (c.get("tgt_share") or 0) >= 0.26, 1.18),
        FlagSpec("SOFT", MATCHUP, lambda c: (c.get("opp_pass_cov_pctl") or 50) <= 30, 1.15),
    ]
    players = [{
        "name": "Test WR", "team": "LAR", "adp": 12.0, "base": 0.20, "tgt_share": 0.30,
        "weeks": [
            {"wk": 1, "opp": "SEA", "home": True, "dome": False, "opp_pass_cov_pctl": 20, "of": None},
            {"wk": 7, "bye": True},
        ],
    }]
    recs = build_position("WR", players, specs, write=False)
    assert len(recs) == 1
    r = recs[0]
    assert "ALPHA" in r["skill_flags"]             # season flag lit
    wk1 = r["weeks"][0]
    assert set(("ALPHA", "SOFT")).issubset(set(wk1["flags"]))  # both lit week 1
    assert 0 <= wk1["p"] <= 100
    assert r["weeks"][1]["lab"] == "BYE"           # bye handled by shared engine


# ---- integration: boards build on the real store ----
def test_boards_build_on_real_store():
    from bbdfs import bestball, dfs
    bb = bestball.build_board()
    df = dfs.build_board()
    assert len(bb) > 100 and "bb_score" in bb.columns
    assert len(df) > 100 and any(c.startswith("p_w") for c in df.columns)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for f in fns:
        f()
        print("ok  ", f.__name__)
    print(f"\n{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
