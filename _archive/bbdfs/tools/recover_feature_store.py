"""recover_feature_store — NON-DESTRUCTIVE diagnosis + recovery for the 139 -> 81 column loss.

The audit found the live features.json has 81 columns; the complete 139-column store
survives only in _prebuild_backup_20260619_171848/. The append-only ingest chain dropped
58 columns silently (every signal from ingest_advanced2..10) when a partial re-run executed
only build_features -> ingest_advanced -> ingest_defense -> reweight.

This tool:
  1. DIAGNOSES — prints exactly which columns the live store lost vs the backup.
  2. RECOVERS (optional) — writes features.recovered.json from the backup snapshot WITHOUT
     overwriting the live file. Review, then promote manually.

It never deletes or overwrites the live store. The real fix is to run the orchestrated
rebuild (refactor/pipeline.py) so all stages run in order under integrity checks — this
tool is the safety net + diagnosis.

Usage:
  python3 bbdfs/tools/recover_feature_store.py            # diagnose only
  python3 bbdfs/tools/recover_feature_store.py --write    # also write features.recovered.json
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = os.path.join(ROOT, "features.json")
BACKUP = os.path.join(ROOT, "_prebuild_backup_20260619_171848", "features.json")


def _cols(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["meta"]["cols"]


def main(write=False):
    if not os.path.exists(LIVE):
        print(f"live store not found at {LIVE}")
        return 1
    if not os.path.exists(BACKUP):
        print(f"backup not found at {BACKUP}; run the orchestrated rebuild instead")
        return 1
    live, backup = _cols(LIVE), _cols(BACKUP)
    lost = [c for c in backup if c not in live]
    gained = [c for c in live if c not in backup]
    print(f"live cols:   {len(live)}")
    print(f"backup cols: {len(backup)}")
    print(f"LOST in live ({len(lost)}): {lost}")
    if gained:
        print(f"newer in live ({len(gained)}): {gained}")
    if write:
        out = os.path.join(ROOT, "features.recovered.json")
        with open(BACKUP, encoding="utf-8") as fh:
            blob = json.load(fh)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(blob, fh, ensure_ascii=False)
        print(f"\nwrote {out} (backup snapshot, {len(backup)} cols).")
        print("REVIEW, then promote manually if correct:")
        print("  mv features.recovered.json features.json   # (and regenerate features.csv)")
        print("NOTE: backup non-defense columns date to 2026-06-19; prefer a clean "
              "refactor/pipeline.py rebuild if upstream sources changed since.")
    else:
        print("\n(diagnosis only; pass --write to emit features.recovered.json — non-destructive)")
    return 0


if __name__ == "__main__":
    sys.exit(main(write="--write" in sys.argv))
