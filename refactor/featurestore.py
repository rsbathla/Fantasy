#!/usr/bin/env python3
"""
featurestore — load ONCE, merge declaratively, write ONCE (atomically).

Replaces the 12 copy-pasted "read features.csv -> for f in feats: f[col]=... ->
rebuild cols -> rewrite csv + json" scripts. A source becomes DATA (a SourceSpec),
not code. Two structural fixes vs the live chain:
  1. ATOMIC csv write (live CSV write is NOT atomic; only the JSON was) -> a crash
     can no longer leave features.csv truncated and out-of-sync with features.json.
  2. csv + json are written from the SAME in-memory rows in one call -> they cannot
     diverge in column set or row order.
Every merge records provenance (which spec wrote which column) for the registry.
"""
import csv, os, tempfile
from dataclasses import dataclass, field
from typing import Callable, Optional
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # repo root for `core`
import core

fn = core.fn


@dataclass
class SourceSpec:
    name: str                                  # provenance label
    csv_path: Optional[str] = None             # source CSV (relative to repo root)
    key_col: str = "Player"                    # source column joined via fn()
    positions: Optional[set] = None            # restrict merge to these board positions
    colmap: dict = field(default_factory=dict) # {out_col: (in_col, parser)}
    transform: Optional[Callable] = None       # fn(src_row|None, feat_row) for computed cols


class FeatureStore:
    def __init__(self, root=None):
        self.root = root or core.HERE
        self.rows = []
        self.provenance = {}   # column -> spec name that introduced it

    def load(self):
        with open(os.path.join(self.root, "features.csv"), encoding="utf-8") as fh:
            self.rows = list(csv.DictReader(fh))
        for c in (self.rows[0].keys() if self.rows else []):
            self.provenance.setdefault(c, "build_features")
        return self

    def apply(self, spec: SourceSpec):
        src = {}
        if spec.csv_path:
            p = os.path.join(self.root, spec.csv_path)
            if os.path.exists(p):
                for r in csv.DictReader(open(p, encoding="utf-8")):
                    src[fn(r[spec.key_col])] = r
        n = 0
        for f in self.rows:
            if spec.positions and f.get("pos") not in spec.positions:
                continue
            row = src.get(fn(f["name"]))
            hit = False
            for out_col, (in_col, parser) in spec.colmap.items():
                if row is not None and in_col in row:
                    v = parser(row[in_col])
                    if v is not None:
                        f[out_col] = v
                        self.provenance[out_col] = spec.name
                        hit = True
            if spec.transform:
                added = spec.transform(row, f) or []
                for c in added:
                    self.provenance[c] = spec.name
                hit = hit or bool(added)
            n += int(hit)
        return n

    def columns(self):
        cols = []
        for f in self.rows:
            for c in f:
                if c not in cols:
                    cols.append(c)
        return cols

    def save(self):
        cols = self.columns()
        # ATOMIC csv (tmp + os.replace) — the fix for the non-atomic live write
        d = self.root
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(self.rows)
        os.replace(tmp, os.path.join(d, "features.csv"))
        core.safe_json_dump({"meta": {"n": len(self.rows), "cols": cols,
                                      "provenance": self.provenance},
                             "players": self.rows}, os.path.join(d, "features.json"))
        return cols


def merge_sources(specs, root=None):
    """Load once, apply every spec, write once. The whole ingest chain in one pass."""
    fs = FeatureStore(root).load()
    counts = {s.name: fs.apply(s) for s in specs}
    cols = fs.save()
    return fs, counts, cols
