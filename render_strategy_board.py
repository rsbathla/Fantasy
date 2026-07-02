#!/usr/bin/env python3
"""render_strategy_board.py -> draft_strategy_board.html

Renders the 12-slot x 3-strategy x 18-round draft strategy board as a self-contained HTML
from strategy_board.json. The HTML is inline CSS/JS (no localStorage, no external dependencies).
Theme: Deep Enterprise Green (Deep-green #003c33 hero, white canvas, Space Grotesk + Inter).

strategy_board.json is AUTHORED by a strategist agent against an ADP snapshot — this script
re-renders it fresh each pipeline run (so the mtime staleness gate passes) while the hero band
shows its snapshot vintage honestly. Do NOT regenerate strategy_board.json here.
"""
import os
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

SRC  = os.path.join(HERE, 'strategy_board.json')
DEST = os.path.join(HERE, 'draft_strategy_board.html')

POS_COLORS = {
    'QB': '#1863dc',
    'RB': '#00875a',
    'WR': '#9254de',
    'TE': '#d46b08',
}

CHECKPOINT_FLOORS = {
    'QB': {'R5': 0, 'R7': 1, 'R9': 2, 'R13': 2, 'R18': 2},
    'RB': {'R5': 2, 'R7': 3, 'R9': 3, 'R13': 4, 'R18': 5},
    'WR': {'R5': 2, 'R7': 3, 'R9': 4, 'R13': 5, 'R18': 6},
    'TE': {'R5': 0, 'R7': 0, 'R9': 0, 'R13': 2, 'R18': 2},
}


def esc(s):
    if s is None:
        return ''
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def pos_pill(pos):
    color = POS_COLORS.get(pos, '#666')
    return f'<span class="pos-pill" style="background:{color}">{esc(pos)}</span>'


def value_badge(player):
    # FIX 5: relabeled from 'VALUE' to 'MODEL EDGE' so it cannot be read as
    # "at-or-below ADP price" — it means the model ranks this player above market.
    if player.get('value'):
        return '<span class="value-badge">MODEL EDGE</span>'
    return ''


def capital_gap_chip(player, pick_number, is_stack_pick=False):
    """FIX 5 (+ sign fix in the P5 window pass): CAPITAL GAP chip for every primary-target card.

    gap = player ADP - pick_number (slot's overall pick for this round).
    Positive gap means the pick lands BEFORE the player's ADP -> drafting EARLY (capital ahead
    of market; you're reaching). Negative/zero means the pick is AT or AFTER his ADP (market
    price or value). This matches strategy_board.json window.capital_at_prefer.

    Display:
      gap > 0  -> '+N early'   (coral + bold warning when N>6 AND is_stack_pick)
      gap <= 0 -> 'at/after ADP'  (green)
    """
    adp = player.get('adp')
    if adp is None or pick_number is None:
        return ''
    gap = round(adp - pick_number)
    if gap > 0:
        warn_cls = ' cap-gap-warn' if (gap > 6 and is_stack_pick) else ''
        return (
            f'<span class="cap-gap cap-gap-early{warn_cls}" '
            f'title="Drafting {gap} pick(s) before ADP — reach warning when &gt;6 on a stack pick">'
            f'+{gap} early</span>'
        )
    else:
        return (
            f'<span class="cap-gap cap-gap-value" '
            f'title="At or after ADP — no capital gap">at/after ADP</span>'
        )


WINDOW_CLASS_CSS = {
    'flexible': 'win-flexible',
    'unavoidable-premium': 'win-unavoidable',
    'conscious-stack-premium': 'win-conscious',
}
WINDOW_CLASS_LABEL = {
    'flexible': 'FLEXIBLE',
    'unavoidable-premium': 'UNAVOIDABLE PREMIUM',
    'conscious-stack-premium': 'CONSCIOUS STACK PREMIUM',
}


def render_window_line(w):
    """P5: latest-safe WINDOW line for stack-pick cards.

    strategy_board.json window contract: {earliest, latest, prefer, p_at_prefer,
    capital_at_prefer, class, note}. Shown as e.g. 'R6–R7 · prefer R7 (57% · +1.6)'
    with a class-colored chip (flexible = green outline, unavoidable-premium = neutral,
    conscious-stack-premium = coral). The note rides in the title tooltip.
    """
    if not w:
        return ''
    cls = WINDOW_CLASS_CSS.get(w.get('class'), 'win-unavoidable')
    label = WINDOW_CLASS_LABEL.get(w.get('class'), esc(w.get('class', '')))
    p_pct = w.get('p_at_prefer')
    p_str = f'{p_pct*100:.0f}%' if isinstance(p_pct, (int, float)) else '?'
    cap = w.get('capital_at_prefer')
    cap_str = f'{cap:+.1f}' if isinstance(cap, (int, float)) else '?'
    rng = f"R{w.get('earliest','?')}–R{w.get('latest','?')}"
    return (
        f'<div class="win-line" title="{esc(w.get("note",""))}">'
        f'<span class="win-chip {cls}">{label}</span>'
        f'<span class="win-range">{rng} · prefer R{w.get("prefer","?")} ({p_str} · {cap_str})</span>'
        f'</div>'
    )


def tier_badge(tier):
    cls = 'tier-elite' if tier == 'ELITE' else ('tier-high' if tier == 'HIGH' else 'tier-mid')
    return f'<span class="tier-badge {cls}">{esc(tier)}</span>'


def render_player_chip(p, is_stack=False, compact=False, pick_number=None):
    adp = p.get('adp')
    adp_str = f'{adp:.1f}' if adp is not None else '—'
    adj = p.get('adj_rank', '')
    w17 = p.get('w17_opp', '')
    stack_cls = ' stack-chip' if is_stack else ''
    if compact:
        return (
            f'<span class="player-chip{stack_cls}">'
            f'{pos_pill(p.get("pos","?"))}'
            f'<span class="chip-name">{esc(p.get("name","?"))}</span>'
            f'<span class="chip-team">{esc(p.get("team",""))}</span>'
            f'<span class="chip-adp">ADP {adp_str}</span>'
            f'{value_badge(p)}'
            f'</span>'
        )
    # FIX 5: capital gap chip on every primary-target (non-compact) player card.
    cap_gap = capital_gap_chip(p, pick_number, is_stack_pick=is_stack)
    return (
        f'<div class="player-card{stack_cls}">'
        f'<div class="pc-top">'
        f'{pos_pill(p.get("pos","?"))}'
        f'<span class="pc-name">{esc(p.get("name","?"))}</span>'
        f'{tier_badge(p.get("tier",""))}'
        f'{value_badge(p)}'
        f'{cap_gap}'
        f'</div>'
        f'<div class="pc-meta">'
        f'<span>ADP <b>{adp_str}</b></span>'
        f'<span>adj <b>{adj}</b></span>'
        f'<span class="pc-team">{esc(p.get("team",""))}</span>'
        f'<span class="pc-w17">W17 vs {esc(w17)}</span>'
        f'</div>'
        f'</div>'
    )


def render_pivot_chip(p):
    adp = p.get('adp')
    adp_str = f'{adp:.1f}' if adp is not None else '—'
    stack_cls = ' stack-chip' if p.get('stack_pick') else ''
    return (
        f'<span class="pivot-chip{stack_cls}">'
        f'{pos_pill(p.get("pos","?"))}'
        f'<span class="chip-name">{esc(p.get("name","?"))}</span>'
        f'<span class="chip-team">{esc(p.get("team",""))}</span>'
        f'<span class="chip-adp">{adp_str}</span>'
        f'{value_badge(p)}'
        f'</span>'
    )


def render_round_card(r_id, r_data, is_late, pick_number=None):
    primary = r_data.get('primary', [])
    pivots = r_data.get('pivots', [])
    why = r_data.get('why', '')
    stack_pick = r_data.get('stack_pick', False)

    round_cls = 'round-card'
    if stack_pick:
        round_cls += ' round-stack'
    if is_late:
        round_cls += ' round-late'

    stack_mark = ''
    if stack_pick:
        stack_mark = '<span class="stack-mark">STACK</span>'

    if is_late:
        # Pool rendering for R14-18
        pool_chips = ''.join(render_player_chip(p, compact=True) for p in primary)
        pivots_html = ''
        if pivots:
            pivot_chips = ''.join(render_pivot_chip(p) for p in pivots)
            pivots_html = f'<div class="pivots-row"><span class="pivots-label">Pivots</span>{pivot_chips}</div>'
        return (
            f'<div class="{round_cls}">'
            f'<div class="rc-header"><span class="rc-rnum">R{r_id}</span>{stack_mark}</div>'
            f'<div class="pool-label">POOL</div>'
            f'<div class="pool-chips">{pool_chips}</div>'
            f'{pivots_html}'
            f'<div class="rc-why">{esc(why)}</div>'
            f'</div>'
        )

    # Single primary target for R1-R13
    # FIX 5: pass pick_number so the capital gap chip can be computed.
    primary_html = ''
    if primary:
        p = primary[0]
        primary_html = render_player_chip(p, is_stack=stack_pick, pick_number=pick_number)

    # P5: latest-safe window line (window contract lives on the round entry).
    window_html = render_window_line(r_data.get('window'))

    pivots_html = ''
    if pivots:
        pivot_chips = ''.join(render_pivot_chip(p) for p in pivots)
        pivots_html = f'<div class="pivots-row"><span class="pivots-label">Pivots</span>{pivot_chips}</div>'

    return (
        f'<div class="{round_cls}">'
        f'<div class="rc-header"><span class="rc-rnum">R{r_id}</span>{stack_mark}</div>'
        f'{primary_html}'
        f'{window_html}'
        f'{pivots_html}'
        f'<div class="rc-why">{esc(why)}</div>'
        f'</div>'
    )


def render_checkpoints(cp):
    if not cp:
        return ''
    floors_ok = cp.get('floors_ok', {})
    rb1_round = cp.get('rb1_round', '?')
    qb1_round = cp.get('qb1_round', '?')
    te1_round = cp.get('te1_round', '?')
    env = cp.get('envelope_target', {})

    def ck_row(label, cp_key, pos, rnd_key):
        count = cp.get(rnd_key, {}).get(pos, 0)
        floor = CHECKPOINT_FLOORS.get(pos, {}).get(label, 0)
        ok = count >= floor
        cls = 'cp-pass' if ok else 'cp-fail'
        icon = '✓' if ok else '✗'
        return (
            f'<span class="cp-cell {cls}">'
            f'<span class="cp-pos">{pos}</span>'
            f'<span class="cp-cnt">{count}</span>'
            f'<span class="cp-floor">/{floor}</span>'
            f'<span class="cp-icon">{icon}</span>'
            f'</span>'
        )

    rows = ''
    for label, rnd_key in [('R5','5'),('R7','7'),('R9','9'),('R13','13'),('R18','18')]:
        rows += f'<div class="cp-checkpoint"><span class="cp-label">{label}</span>'
        for pos in ['QB','RB','WR','TE']:
            rows += ck_row(label, rnd_key, pos, rnd_key)
        rows += '</div>'

    first_picks = (
        f'<div class="cp-firsts">'
        f'<span>RB1 R{rb1_round}</span>'
        f'<span>QB1 R{qb1_round}</span>'
        f'<span>TE1 R{te1_round}</span>'
        f'</div>'
    )

    all_ok = all(floors_ok.values()) if floors_ok else True
    ok_badge = ('<span class="floors-ok">FLOORS OK</span>' if all_ok
                else '<span class="floors-fail">FLOOR VIOLATION</span>')

    # deliberate_early_qb (strategist-authored, present only on strategies whose
    # floors_ok.qb_late is false): render an EARLY-QB: DELIBERATE chip (coral
    # outline) with the rationale as tooltip, plus the rationale in small type
    # under the strip — so a qb_late fail reads as a documented conscious
    # exception, not a broken build.
    deq = cp.get('deliberate_early_qb', '')
    deq_chip = ''
    deq_note = ''
    if deq:
        deq_chip = (
            f'<span class="early-qb-chip" title="{esc(deq)}">EARLY-QB: DELIBERATE</span>'
        )
        deq_note = f'<div class="early-qb-note">{esc(deq)}</div>'

    return (
        f'<div class="checkpoints">'
        f'<div class="cp-title">CHECKPOINTS {ok_badge}{deq_chip}</div>'
        f'{rows}'
        f'{first_picks}'
        f'{deq_note}'
        f'</div>'
    )


def render_stack_plan(sp):
    if not sp:
        return ''
    parts = []
    for label, key in [('Primary Stack', 'primary'), ('Secondary Stack', 'secondary')]:
        s = sp.get(key)
        if not s:
            continue
        off = esc(s.get('offense', ''))
        qb = esc(s.get('qb', ''))
        pieces = esc(s.get('pieces', ''))
        target_rounds = esc(s.get('target_rounds', ''))
        w17_bb = esc(s.get('w17_bringback', ''))
        # P5: latest-safe windows summary for this stack's designated pieces.
        window_text = esc(s.get('window_text', ''))
        window_row = (
            f'<div class="sb-row sb-windows"><span class="sb-key">Windows:</span> {window_text}</div>'
            if window_text else ''
        )
        parts.append(
            f'<div class="stack-block">'
            f'<div class="sb-label">{label}</div>'
            f'<div class="sb-offense">{off}</div>'
            f'<div class="sb-row"><span class="sb-key">QB:</span> {qb}</div>'
            f'<div class="sb-row"><span class="sb-key">Pieces:</span> {pieces}</div>'
            f'<div class="sb-row"><span class="sb-key">Rounds:</span> {target_rounds}</div>'
            f'{window_row}'
            f'<div class="sb-row sb-bringback"><span class="sb-key">W17 bring-back:</span> {w17_bb}</div>'
            f'</div>'
        )
    return f'<div class="stack-plan">{"".join(parts)}</div>'


def render_strategy(strat, slot_picks=None):
    sid = strat.get('id', '')
    name = strat.get('name', '')
    archetype = strat.get('archetype', '')
    thesis = strat.get('thesis', '')
    stack_plan = strat.get('stack_plan', {})
    rounds_data = strat.get('rounds', {})
    checkpoints = strat.get('checkpoints', {})
    w17 = strat.get('w17', {})
    differentiation = strat.get('differentiation', '')

    # Render round cards
    # FIX 5: pass pick_number (the slot's overall pick for that round) so the
    # capital gap chip can compute gap = pick_number - player_ADP.
    round_cards = ''
    for r_num in range(1, 19):
        r_id = str(r_num)
        r_data = rounds_data.get(r_id, {})
        is_late = r_num >= 14
        # slot_picks is a list of 18 overall pick numbers (index 0 = R1)
        pick_number = slot_picks[r_num - 1] if slot_picks and r_num <= len(slot_picks) else None
        round_cards += render_round_card(r_id, r_data, is_late, pick_number=pick_number)

    w17_summary = w17.get('summary', '') if isinstance(w17, dict) else str(w17)

    return (
        f'<div class="strategy" data-sid="{esc(sid)}">'
        f'<div class="strat-thesis-block">'
        f'<div class="thesis-label">THESIS</div>'
        f'<div class="thesis-text">{esc(thesis)}</div>'
        f'</div>'
        f'{render_stack_plan(stack_plan)}'
        f'<div class="rounds-label">18-ROUND PLAN</div>'
        f'<div class="rounds-grid">{round_cards}</div>'
        f'{render_checkpoints(checkpoints)}'
        f'<div class="w17-bar">'
        f'<span class="w17-label">W17 CORRELATION</span>'
        f'<span class="w17-text">{esc(w17_summary)}</span>'
        f'</div>'
        f'<div class="differentiation">{esc(differentiation)}</div>'
        f'</div>'
    )


def render_slot(slot_id, slot_data):
    picks = slot_data.get('picks', [])
    strategies = slot_data.get('strategies', [])
    # Per-slot LEVERAGE PIVOT (strategist-authored de-chalk note naming the best
    # off-chalk stack reachable from this slot): rendered as a distinct advisory
    # callout at the TOP of the slot section, BEFORE the strategy tabs — outlined
    # panel + coral label so it reads as advisory, not part of any one strategy.
    leverage_pivot = slot_data.get('leverage_pivot', '')
    # First 3 pick numbers for display on slot button
    first_picks = picks[:3] if picks else []
    picks_label = ', '.join(str(p) for p in first_picks) + ('…' if len(picks) > 3 else '')

    tabs_html = ''
    panels_html = ''
    for i, strat in enumerate(strategies):
        sid = strat.get('id', '')
        sname = strat.get('name', '')
        archetype = strat.get('archetype', '')
        active = 'active' if i == 0 else ''
        tabs_html += (
            f'<button class="strat-tab {active}" data-slot="{esc(slot_id)}" data-strat="{esc(sid)}">'
            f'<span class="tab-id">{esc(sid)}</span>'
            f'<span class="tab-name">{esc(sname)}</span>'
            f'<span class="archetype-chip">{esc(archetype)}</span>'
            f'</button>'
        )
        display = 'block' if i == 0 else 'none'
        panels_html += (
            f'<div class="strat-panel" data-slot="{esc(slot_id)}" data-strat="{esc(sid)}" style="display:{display}">'
            f'{render_strategy(strat, slot_picks=picks)}'
            f'</div>'
        )

    lp_html = ''
    if leverage_pivot:
        lp_html = (
            f'<div class="leverage-pivot">'
            f'<span class="lp-label">LEVERAGE PIVOT</span>'
            f'<span class="lp-text">{esc(leverage_pivot)}</span>'
            f'</div>'
        )

    return (
        f'<div class="slot-section" id="slot-{esc(slot_id)}" style="display:none">'
        f'<div class="slot-header">'
        f'<span class="slot-title">Slot {esc(slot_id)}</span>'
        f'<span class="slot-picks">Picks: {esc(picks_label)}</span>'
        f'</div>'
        f'{lp_html}'
        f'<div class="strat-tabs">{tabs_html}</div>'
        f'<div class="strat-panels">{panels_html}</div>'
        f'</div>'
    )


def render_html(data):
    meta = data.get('_meta', {})
    adp_snapshot = meta.get('adp_snapshot', 'Unknown')
    built = meta.get('built', '')
    evidence = meta.get('evidence', 'WINNING_STRUCTURE.md')
    n_slots = meta.get('n_slots', 12)
    n_strategies = meta.get('n_strategies', 36)
    draft_format = meta.get('draft_format', {})
    n_rounds = draft_format.get('n_rounds', 18)

    # _meta.capital_honesty (strategist-authored): surface the measured stack-piece
    # capital gap as one honest line in the hero band, under the snapshot note.
    capital_honesty = meta.get('capital_honesty') or {}
    cap_line_html = ''
    if capital_honesty:
        gap = capital_honesty.get('mean_stack_capital_gap_picks_ahead_of_adp')
        gap_str = f'+{gap}' if gap is not None else '+?'
        cap_line_html = (
            f'<p class="hero-capital">Stack pieces average <b>{esc(gap_str)} picks ahead of ADP</b> '
            f'by slot structure &mdash; capital chips mark each pick; wait where your room allows.</p>'
        )

    # Render all slots
    all_slots_html = ''
    slot_buttons_html = ''
    for slot_id in [str(i) for i in range(1, 13)]:
        slot_data = data['slots'].get(slot_id, {})
        picks = slot_data.get('picks', [])
        first_picks = picks[:3] if picks else []
        picks_label = ', '.join(str(p) for p in first_picks)
        active = 'active' if slot_id == '1' else ''
        slot_buttons_html += (
            f'<button class="slot-btn {active}" data-slot="{esc(slot_id)}">'
            f'<span class="sb-slot">Slot {esc(slot_id)}</span>'
            f'<span class="sb-picks">{esc(picks_label)}</span>'
            f'</button>'
        )
        all_slots_html += render_slot(slot_id, slot_data)

    render_ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Draft Strategy Board — 2026 Best Ball</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{
--green:#003c33;--green2:#0a4d43;--palegreen:#edfce9;--near:#17171c;--black:#000;
--canvas:#ffffff;--stone:#eeece7;--ink:#212121;--muted:#93939f;--slate:#75758a;
--hair:#d9d9dd;--border:#e5e7eb;--cardb:#f2f2f2;--coral:#ff7759;--softcoral:#ffad9b;--blue:#1863dc;
--disp:'Space Grotesk',Inter,ui-sans-serif,system-ui;--body:Inter,Arial,ui-sans-serif,system-ui;
--mono:'Space Grotesk',ui-monospace,Menlo,monospace;
--pos-qb:#1863dc;--pos-rb:#00875a;--pos-wr:#9254de;--pos-te:#d46b08;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--canvas);color:var(--ink);font:15px/1.5 var(--body);-webkit-font-smoothing:antialiased}}
.mono{{font-family:var(--mono);text-transform:uppercase;letter-spacing:.28px}}
/* ---- HERO BAND ---- */
.hero{{background:var(--green);color:#fff;padding:52px 24px 40px}}
.herox{{max-width:1160px;margin:0 auto}}
.hero h1{{font-family:var(--disp);font-weight:500;font-size:clamp(36px,5.5vw,64px);line-height:1.05;letter-spacing:-1.2px;color:#fff;margin-bottom:12px}}
.hero-adp{{font-size:16px;color:rgba(255,255,255,.9);font-family:var(--body);margin:8px 0 4px}}
.hero-adp b{{color:#fff}}
/* ---- CAPITAL HONESTY LINE (hero, from _meta.capital_honesty) ---- */
.hero-capital{{font-size:13.5px;color:rgba(255,255,255,.75);margin:2px 0 4px;font-family:var(--body)}}
.hero-capital b{{color:var(--softcoral)}}
.hero-evidence{{font-size:13px;color:rgba(255,255,255,.55);margin:4px 0 0;font-family:var(--mono);letter-spacing:.3px}}
.hero-meta{{display:flex;gap:20px 32px;flex-wrap:wrap;margin-top:20px;font-size:12.5px;color:rgba(255,255,255,.55)}}
.hero-meta b{{color:#fff}}
/* ---- SLOT PICKER BAR ---- */
.slot-picker{{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.96);backdrop-filter:blur(10px);border-bottom:1px solid var(--border);padding:10px 24px}}
.slot-picker-inner{{max-width:1160px;margin:0 auto;display:flex;gap:6px;flex-wrap:wrap;align-items:center}}
.slot-btn{{background:#fff;color:var(--ink);border:1px solid var(--hair);border-radius:10px;padding:6px 12px;cursor:pointer;font-family:var(--body);font-size:13px;transition:.12s;text-align:left;min-width:86px}}
.slot-btn:hover{{border-color:var(--near)}}
.slot-btn.active{{background:var(--near);color:#fff;border-color:var(--near)}}
.sb-slot{{display:block;font-weight:600;font-size:13px}}
.sb-picks{{display:block;font-size:11px;color:var(--muted);font-family:var(--mono);letter-spacing:.2px}}
.slot-btn.active .sb-picks{{color:rgba(255,255,255,.65)}}
/* ---- CANVAS ---- */
.canvas{{max-width:1160px;margin:0 auto;padding:28px 24px 80px}}
/* ---- SLOT SECTION ---- */
.slot-section{{}}
.slot-header{{display:flex;align-items:baseline;gap:14px;padding:0 0 16px;border-bottom:1px solid var(--border);margin-bottom:16px}}
.slot-title{{font-family:var(--disp);font-weight:500;font-size:28px;letter-spacing:-.5px;color:var(--near)}}
.slot-picks{{font-size:13px;color:var(--muted);font-family:var(--mono)}}
/* ---- LEVERAGE PIVOT (per-slot advisory callout, before strategy tabs) ---- */
.leverage-pivot{{border:1.5px solid var(--coral);background:#fff;border-radius:10px;padding:12px 16px;margin-bottom:16px;display:flex;gap:12px;align-items:flex-start}}
.lp-label{{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--coral);letter-spacing:.5px;flex-shrink:0;margin-top:2px}}
.lp-text{{font-size:13.5px;color:var(--ink);line-height:1.5}}
/* ---- STRATEGY TABS ---- */
.strat-tabs{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:20px}}
.strat-tab{{background:#fff;border:1px solid var(--hair);border-radius:10px;padding:10px 16px;cursor:pointer;font-family:var(--body);text-align:left;transition:.12s;min-width:200px;max-width:340px}}
.strat-tab:hover{{border-color:var(--near)}}
.strat-tab.active{{border-color:var(--green);box-shadow:0 0 0 2px var(--green)}}
.tab-id{{font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:.4px;display:block}}
.tab-name{{font-family:var(--disp);font-weight:500;font-size:14px;color:var(--near);display:block;margin:2px 0}}
.archetype-chip{{font-size:11px;color:var(--slate);font-family:var(--mono);letter-spacing:.2px;display:block}}
/* ---- STRATEGY CONTENT ---- */
.strategy{{}}
/* ---- THESIS ---- */
.strat-thesis-block{{background:var(--palegreen);border:1px solid #c3efd9;border-radius:12px;padding:16px 20px;margin-bottom:16px}}
.thesis-label{{font-family:var(--mono);font-size:10px;color:var(--green);letter-spacing:.5px;font-weight:600;margin-bottom:6px}}
.thesis-text{{font-size:14px;color:var(--ink);line-height:1.55}}
/* ---- STACK PLAN ---- */
.stack-plan{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
.stack-block{{flex:1;min-width:240px;background:#f9f9fb;border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
.sb-label{{font-family:var(--mono);font-size:10px;font-weight:600;color:var(--green);letter-spacing:.5px;margin-bottom:6px}}
.sb-offense{{font-family:var(--disp);font-weight:600;font-size:18px;letter-spacing:-.2px;color:var(--near);margin-bottom:6px}}
.sb-row{{font-size:13px;color:var(--slate);margin-bottom:3px;line-height:1.4}}
.sb-key{{color:var(--ink);font-weight:600}}
.sb-bringback{{color:var(--coral);font-size:12.5px}}
/* ---- ROUNDS GRID ---- */
.rounds-label{{font-family:var(--mono);font-size:10px;letter-spacing:.5px;color:var(--muted);font-weight:600;margin-bottom:10px;text-transform:uppercase}}
.rounds-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin-bottom:20px}}
/* ---- ROUND CARD ---- */
.round-card{{background:#fff;border:1px solid var(--border);border-radius:10px;padding:10px 12px;position:relative}}
.round-card.round-stack{{border-color:#c3efd9;background:#f5fdf7}}
.round-card.round-late{{background:#fdfcfb;border-color:var(--cardb)}}
.rc-header{{display:flex;align-items:center;gap:6px;margin-bottom:6px}}
.rc-rnum{{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.5px}}
.stack-mark{{font-family:var(--mono);font-size:9px;font-weight:700;background:var(--green);color:#fff;border-radius:4px;padding:2px 6px;letter-spacing:.4px}}
/* ---- PLAYER CARD ---- */
.player-card{{margin-bottom:6px}}
.player-card.stack-chip{{border-left:3px solid var(--green);padding-left:6px}}
.pc-top{{display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-bottom:3px}}
.pc-name{{font-family:var(--disp);font-weight:500;font-size:14px;letter-spacing:-.2px;color:var(--near)}}
.pc-meta{{font-size:11.5px;color:var(--slate);display:flex;gap:8px;flex-wrap:wrap}}
.pc-team{{font-weight:600;color:var(--ink)}}
.pc-w17{{color:var(--muted)}}
/* ---- POS PILL ---- */
.pos-pill{{font-family:var(--mono);font-size:9px;font-weight:700;color:#fff;border-radius:4px;padding:2px 5px;letter-spacing:.3px;text-transform:uppercase;flex-shrink:0}}
/* ---- TIER BADGE ---- */
.tier-badge{{font-family:var(--mono);font-size:9px;font-weight:600;border-radius:4px;padding:2px 6px;letter-spacing:.3px}}
.tier-elite{{background:var(--palegreen);color:var(--green)}}
.tier-high{{background:#fffbe6;color:#7c5a00}}
.tier-mid{{background:var(--cardb);color:var(--muted)}}
/* ---- MODEL EDGE BADGE (FIX 5: relabeled from VALUE) ---- */
.value-badge{{font-family:var(--mono);font-size:9px;font-weight:600;background:var(--coral);color:#fff;border-radius:4px;padding:2px 5px;letter-spacing:.3px}}
/* ---- CAPITAL GAP CHIP (FIX 5) ---- */
.cap-gap{{font-family:var(--mono);font-size:9px;font-weight:600;border-radius:4px;padding:2px 5px;letter-spacing:.2px;flex-shrink:0}}
.cap-gap-early{{background:#fff0ed;color:var(--coral);border:1px solid var(--softcoral)}}
.cap-gap-early.cap-gap-warn{{background:var(--coral);color:#fff;border-color:var(--coral)}}
.cap-gap-value{{background:var(--palegreen);color:var(--green);border:1px solid #c3efd9}}
/* ---- P5 LATEST-SAFE WINDOW LINE (stack picks) ---- */
.win-line{{display:flex;gap:6px;align-items:center;margin:4px 0 5px;flex-wrap:wrap}}
.win-chip{{font-family:var(--mono);font-size:8.5px;font-weight:700;border-radius:4px;padding:2px 6px;letter-spacing:.4px;flex-shrink:0}}
.win-flexible{{background:#fff;color:var(--green);border:1.5px solid var(--green)}}
.win-unavoidable{{background:var(--cardb);color:var(--slate);border:1px solid var(--hair)}}
.win-conscious{{background:var(--coral);color:#fff;border:1px solid var(--coral)}}
.win-range{{font-family:var(--mono);font-size:10px;color:var(--ink);letter-spacing:.2px}}
.sb-windows{{font-family:var(--mono);font-size:10.5px;color:var(--slate)}}
/* ---- PIVOTS ---- */
.pivots-row{{display:flex;gap:4px;flex-wrap:wrap;margin:5px 0;align-items:center}}
.pivots-label{{font-family:var(--mono);font-size:9px;color:var(--muted);letter-spacing:.3px;flex-shrink:0;margin-right:2px}}
.pivot-chip{{display:inline-flex;align-items:center;gap:3px;font-size:11px;color:var(--slate);background:var(--cardb);border:1px solid var(--hair);border-radius:6px;padding:2px 6px;flex-wrap:wrap}}
.pivot-chip.stack-chip{{border-color:#c3efd9;background:#f5fdf7}}
.chip-name{{font-weight:500;color:var(--ink)}}
.chip-team{{color:var(--muted);font-size:10px}}
.chip-adp{{font-family:var(--mono);font-size:10px;color:var(--slate)}}
/* ---- PLAYER CHIP (compact, for pools) ---- */
.player-chip{{display:inline-flex;align-items:center;gap:4px;background:#fff;border:1px solid var(--border);border-radius:8px;padding:3px 8px;margin:2px;font-size:12px;flex-shrink:0}}
.player-chip.stack-chip{{border-color:#c3efd9;background:#f5fdf7}}
/* ---- POOL ---- */
.pool-label{{font-family:var(--mono);font-size:9px;letter-spacing:.5px;color:var(--muted);font-weight:600;margin-bottom:4px}}
.pool-chips{{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:5px}}
/* ---- WHY ---- */
.rc-why{{font-size:11.5px;color:var(--slate);line-height:1.4;margin-top:4px;font-style:italic}}
/* ---- CHECKPOINTS ---- */
.checkpoints{{background:#f9f9fb;border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:16px}}
.cp-title{{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.5px;color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.floors-ok{{background:var(--palegreen);color:var(--green);border-radius:4px;padding:2px 7px;font-size:9px;font-family:var(--mono)}}
.floors-fail{{background:#fff0ed;color:var(--coral);border-radius:4px;padding:2px 7px;font-size:9px;font-family:var(--mono)}}
.cp-checkpoint{{display:flex;align-items:center;gap:6px;margin-bottom:5px;flex-wrap:wrap}}
.cp-label{{font-family:var(--mono);font-size:10px;font-weight:600;color:var(--ink);min-width:24px}}
.cp-cell{{display:inline-flex;align-items:center;gap:2px;border:1px solid var(--hair);border-radius:5px;padding:2px 6px;font-size:11px}}
.cp-cell.cp-pass{{background:var(--palegreen);border-color:#c3efd9}}
.cp-cell.cp-fail{{background:#fff0ed;border-color:var(--softcoral)}}
.cp-pos{{font-family:var(--mono);font-size:9px;color:var(--muted);margin-right:2px}}
.cp-cnt{{font-weight:700;font-size:12px}}
.cp-floor{{font-size:10px;color:var(--muted)}}
.cp-icon{{font-size:11px;margin-left:2px}}
.cp-pass .cp-icon{{color:var(--green)}}
.cp-fail .cp-icon{{color:var(--coral)}}
.cp-firsts{{display:flex;gap:10px;margin-top:8px;font-size:12px;color:var(--slate);font-family:var(--mono);flex-wrap:wrap}}
.cp-firsts span{{background:var(--cardb);border-radius:5px;padding:2px 7px}}
/* ---- EARLY-QB: DELIBERATE (documented conscious exception to QB-late floor) ---- */
.early-qb-chip{{border:1px solid var(--coral);color:var(--coral);background:#fff;border-radius:4px;padding:2px 7px;font-size:9px;font-family:var(--mono);font-weight:600;letter-spacing:.3px;cursor:help}}
.early-qb-note{{font-size:11.5px;color:var(--slate);line-height:1.45;margin-top:8px;border-top:1px dashed var(--softcoral);padding-top:6px}}
/* ---- W17 CORRELATION ---- */
.w17-bar{{background:#fff7f5;border:1px solid var(--softcoral);border-radius:8px;padding:10px 14px;margin-bottom:12px;display:flex;gap:10px;align-items:flex-start}}
.w17-label{{font-family:var(--mono);font-size:9px;font-weight:700;color:var(--coral);letter-spacing:.4px;flex-shrink:0;margin-top:2px}}
.w17-text{{font-size:13px;color:var(--ink);line-height:1.4}}
/* ---- DIFFERENTIATION ---- */
.differentiation{{font-size:12.5px;color:var(--muted);border-top:1px solid var(--hair);padding-top:10px;line-height:1.5}}
/* ---- FOOTER ---- */
.footer{{max-width:1160px;margin:0 auto;padding:0 24px 60px;color:var(--muted);font-size:12px;border-top:1px solid var(--hair);padding-top:20px}}
@media(max-width:700px){{
  .hero{{padding:32px 16px 28px}}
  .slot-picker{{padding:8px 12px}}
  .canvas{{padding:20px 14px 60px}}
  .rounds-grid{{grid-template-columns:1fr 1fr}}
  .strat-tab{{min-width:140px}}
  .stack-plan{{flex-direction:column}}
}}
</style>
</head>
<body>
<section class="hero">
  <div class="herox">
    <h1>Draft Strategy Board</h1>
    <p class="hero-adp">Strategies authored against ADP snapshot: <b>{esc(adp_snapshot)}</b></p>
    {cap_line_html}
    <p class="hero-evidence">Evidence base: {esc(evidence)}</p>
    <div class="hero-meta">
      <span><b>{n_slots}</b> draft slots</span>
      <span><b>{n_strategies}</b> strategies</span>
      <span><b>{n_rounds}</b> rounds</span>
      <span><b>{esc(built)}</b> authored</span>
      <span>rendered <b>{esc(render_ts)}</b></span>
    </div>
  </div>
</section>
<div class="slot-picker">
  <div class="slot-picker-inner">
    {slot_buttons_html}
  </div>
</div>
<div class="canvas">
  {all_slots_html}
</div>
<div class="footer">
  Draft Strategy Board &mdash; 2026 Best Ball &mdash; {n_slots}&times;{n_strategies//n_slots} strategies &times; {n_rounds} rounds.
  Rendered {esc(render_ts)}. Evidence: {esc(evidence)}.
</div>
<script>
(function(){{
  // Show first slot on load
  var firstSlot = document.querySelector('.slot-section');
  if(firstSlot) firstSlot.style.display='block';

  // Slot picker
  document.querySelector('.slot-picker-inner').addEventListener('click', function(e){{
    var btn = e.target.closest('.slot-btn');
    if(!btn) return;
    var slot = btn.dataset.slot;
    // Update buttons
    document.querySelectorAll('.slot-btn').forEach(function(b){{b.classList.remove('active');}});
    btn.classList.add('active');
    // Show/hide slot sections
    document.querySelectorAll('.slot-section').forEach(function(s){{
      s.style.display = (s.id === 'slot-'+slot) ? 'block' : 'none';
    }});
  }});

  // Strategy tab switching (delegated)
  document.addEventListener('click', function(e){{
    var tab = e.target.closest('.strat-tab');
    if(!tab) return;
    var slot = tab.dataset.slot;
    var strat = tab.dataset.strat;
    // Update tabs for this slot
    document.querySelectorAll('.strat-tab[data-slot="'+slot+'"]').forEach(function(t){{
      t.classList.remove('active');
    }});
    tab.classList.add('active');
    // Show/hide panels for this slot
    document.querySelectorAll('.strat-panel[data-slot="'+slot+'"]').forEach(function(p){{
      p.style.display = (p.dataset.strat === strat) ? 'block' : 'none';
    }});
  }});
}})();
</script>
</body>
</html>'''


def main():
    print(f'Reading {SRC}...')
    with open(SRC, encoding='utf-8') as f:
        data = json.load(f)

    print('Rendering HTML...')
    html = render_html(data)

    with open(DEST, 'w', encoding='utf-8') as f:
        f.write(html)

    size = os.path.getsize(DEST)
    print(f'Written: {DEST}  ({size:,} bytes)')


if __name__ == '__main__':
    main()
