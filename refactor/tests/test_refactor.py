#!/usr/bin/env python3
"""Unit tests — the test layer the live repo lacks. Run: python3 -m pytest refactor/tests
   (or `python3 refactor/tests/test_refactor.py` for a dependency-free smoke run)."""
import os, sys
_H=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_H))            # refactor/
sys.path.insert(0, os.path.dirname(os.path.dirname(_H)))  # repo root for core
import numpy as np, pandas as pd
import statlib, parse

def test_pctl_abstain_matches_legacy_formula():
    raw = pd.Series([10.0, 20.0, 30.0, np.nan]); pos = pd.Series(["WR"]*4)
    got = statlib.pctl(raw, pos, fill=None, round_to=1)
    # legacy dfs formula: (rank-0.5)/n*100 over the 3 present, NaN preserved
    assert list(got[:3]) == [16.7, 50.0, 83.3]
    assert pd.isna(got[3])              # abstains, NOT filled to 50

def test_pctl_neutral_fills_absent():
    raw = pd.Series([1.0, 2.0, np.nan]); pos = pd.Series(["RB"]*3)
    got = statlib.pctl(raw, pos, fill=50.0)
    assert got[2] == 50.0               # fusion display policy

def test_pctl_single_eligible_is_neutral():
    got = statlib.pctl(pd.Series([5.0]), pd.Series(["TE"]), fill=None)
    assert got[0] == 50.0

def test_invert():
    raw = pd.Series([1.0, 2.0]); pos = pd.Series(["WR","WR"])
    assert statlib.pctl(raw, pos, invert=True)[0] > statlib.pctl(raw, pos, invert=True)[1]

def test_parsers():
    assert parse.num('"-2.07"') == -2.07
    assert parse.pct("43.5%") == 43.5
    assert parse.pnum("97%Elite") == 97.0
    assert parse.num("garbage") is None

def test_team_resolver():
    assert parse.team_code("Raiders") == "LV"
    assert parse.team_code("Las Vegas Raiders") == "LV"
    assert parse.ab("1PIT") == "PIT"
    assert parse.team_code("LA") == "LAR"

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print("ALL %d PASS" % len(fns))
