"""Atomic, NaN-safe IO helpers.

safe_json_dump is the proven core writer (NaN/Inf -> null, tmp + os.replace so a crash
never leaves a truncated file). load_json/load_csv are the read helpers consumers
re-rolled in nearly every script.
"""
import csv as _csv
import json as _json
import core as _core

safe_json_dump = _core.safe_json_dump
repo_path = _core.P  # repo_path('features.json') -> absolute path under the repo root


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return _json.load(fh)


def load_csv(path):
    with open(path, encoding="utf-8") as fh:
        return list(_csv.DictReader(fh))
