#!/usr/bin/env python3
"""build_flags_v2.py — unified flag builder; replaces build_flags_<POS>.py one position at a time.

    python3 build_flags_v2.py DST        # build one position via the shared engine
    python3 build_flags_v2.py --all      # build every ported position

One engine (flagkit.engine) + one small position model per position (flagkit.<pos>).
As each position reaches byte-parity with its legacy builder, delete the legacy file.
"""
import sys
import importlib
from flagkit import engine

MODELS = {                          # all five positions ported & verified byte-identical
    'QB':  'flagkit.qb',
    'RB':  'flagkit.rb',
    'WR':  'flagkit.wr',
    'TE':  'flagkit.te',
    'DST': 'flagkit.dst',
}


def build_one(pos):
    model = importlib.import_module(MODELS[pos])
    out = engine.build(pos, model)
    print(f"[v2] {pos}: {len(out)} players -> boom/flags_{pos}.json")
    return out


def main(argv):
    if '--all' in argv:
        for pos in MODELS:
            build_one(pos)
        return 0
    if len(argv) < 2 or argv[1] not in MODELS:
        sys.exit(f"usage: build_flags_v2.py [{'|'.join(MODELS)} | --all]")
    build_one(argv[1])
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
