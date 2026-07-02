# archive/

Confirmed-dead and superseded artifacts, moved here 2026-07-02 (verdicts in `../ORPHAN_TRIAGE.md`).
Preserved in git history rather than deleted. `integration_audit.py` excludes this directory,
so nothing here is re-flagged as an orphan. Nothing in the live tree reads any of these.

| File | Origin | Verdict | Replaced by |
|---|---|---|---|
| `player_boom.json` | repo root | DEAD | boom subsystem: `boom/statmenu.json` + `boom/boom_marks.json` |
| `build_player_boom.py` | repo root | DEAD | (produced player_boom.json; nothing reads it) |
| `defender_profiles.json` | `boom/` | SUPERSEDED | `boom/defender_grades.json` (`build_defender_grades.py`, a boom stage) |
| `build_defenders.py` | repo root | DEAD | (produced defender_profiles.json; superseded) |
| `funnel_projection_2026.json` | `boom/` | SUPERSEDED | `boom/defensive_profile.json` per-team `funnels`/`lean_2025`/`lean_2026` |
| `separation.json` | `boom/` | SUPERSEDED | live NGS separation via `fusion.py` (`rec_separation`) + `boom/coverage_route_spec.json` MAN rollups |
| `sis_defenders.json` | `boom/` | SUPERSEDED | SIS ingested directly by `ingest_defense.py` -> `defense.json` unit pctls + top_* lists |
| `receiving_manzone_nfl_2025.csv` | `sis_value/` | SUPERSEDED | split EPA leaderboards `ingest_advanced7/8.py` (`receiving_man.csv`/`receiving_zone.csv`) |
| `cfb_passdef_value_2024.csv` | `sis_value/cfb/` | DEAD | only the 2025 file is read (`build_rookie_db_funnel.py`); held for a possible DB backtest |
| `cfb_passrush_value_2025.csv` | `sis_value/cfb/` | DEAD | defensive CFB signal with no wired rookie-model pathway |
| `cfb_rundef_value_2025.csv` | `sis_value/cfb/` | DEAD | defensive CFB signal with no wired rookie-model pathway |

To restore any file: `git mv archive/<file> <original path>`.
