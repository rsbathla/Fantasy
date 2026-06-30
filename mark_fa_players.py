#!/usr/bin/env python3
"""mark_fa_players.py — Rec 6: honest handling of UNSIGNED free agents.

Verified via web (June 2026) that the team='FA' players (Diggs, Tyreek Hill, Mixon, Najee
Harris, Ekeler, Chubb, Hunt, Hopkins, Allen, Ertz, Waller, Deebo Samuel) are GENUINELY
unsigned -- released after 2025 (mostly injury), not signed anywhere -- not stale data. So we
cannot project a 2026 board for them. Rather than a confusing blank grid, label them clearly
as contingent late-round darts pending a landing spot. Idempotent; runs after the overlay."""
import json, os
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom')
NOTE = ("UNSIGNED FREE AGENT (as of June 2026) — no 2026 team/schedule yet, so no weekly "
        "matchup board. Draftable only as a contingent late-round dart; re-evaluate once he "
        "signs. Prior-role profile: ")
n = 0
for pos in ('QB', 'RB', 'WR', 'TE', 'DST'):
    p = f"{B}/flags_{pos}.json"
    d = json.load(open(p)); ch = False
    for k, v in d.items():
        if v.get('team') == 'FA' and not (v.get('line') or '').startswith('UNSIGNED'):
            v['line'] = NOTE + (v.get('line') or ''); ch = True; n += 1
    if ch:
        json.dump(d, open(p, 'w'), ensure_ascii=False)
print(f"marked {n} unsigned FA players with a clear note")
