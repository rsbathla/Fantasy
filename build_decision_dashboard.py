#!/usr/bin/env python3
"""
build_decision_dashboard.py  (Agent D / Contract 5)  -- DATA-RICH rebuild

Generates bestball/decision_dashboard.html: a self-contained, plain HTML/JS
dashboard that renders the live Best-Ball decision payload (engine/live_tree.json).

DESIGN NOTES
------------
* Self-contained: inline CSS + JS + data. No external scripts / assets / fonts.
* NO custom elements / Web Components / Shadow DOM (hard rule). Plain
  <div>/<table>/<button> + vanilla JS only.
* ONE render entry point  renderDashboard(data)  consumes the exact live_tree.json
  shape produced by engine/run_live.py:
      {
        state: {pick,round,seat,roster[{name,pos,team}],counts{QB,RB,WR,TE},
                anchor, modeled_n, drafted_n, untracked?[], dropped?[]},
        headline: {take,dTitle,dAdv,why},
        tree: {label, branches:[{cond,take,pos,dTitle,dAdv,dW17,reason,
                playoff_up,then:{...}}]},
        board: [ candidates, each with name/pos/team/adp/rank/value/
                proj/ceiling/ceil_pct/cv/spike/bye/w15/w16/w17/w17rank/adv_pct/
                playoff_up + RICH fields stack/scouting/quote/flags[]/tweet
                (+ dTitle/dAdv/dW17 when in the tree) ],
        roster_detail: [ my players, same per-player fields ],
        construction: {counts, targets{QB,RB,WR,TE}, anchor, byes[]}
      }
  The embedded payload below is just the default seed: the real engine output
  (run_live.py -> live_tree.json) drops in unchanged by replacing EMBEDDED_DATA,
  or live via the "Paste a board / Contract-3 JSON" box.

SECTIONS RENDERED
-----------------
  1. HEADER       pick/round/seat, "modeled N of M picks" (+ untracked / dropped
                  names if present), anchor game, roster bye list, position
                  counts vs construction targets (red when below target).
  2. HEADLINE     the recommended pick (player, dTitle/dAdv colour-coded, why).
  3. DECISION TREE collapsible branches (cond/take/deltas/playoff_up/reason +
                  nested then look-ahead).
  4. CANDIDATE BOARD  centerpiece: a sortable / position-filterable table of the
                  full `board`; click a header to sort, click a row to expand a
                  RICH scouting card (stack tag, FLAG warning chips, scouting take,
                  quote, tweet buzz, then metrics); playoff_up / value / deltas
                  colour-coded; rows with a STACK tag are highlighted (green link /
                  amber bring-back) and tree picks are accented.
  5. MY ROSTER    roster_detail as a compact table (Player/Pos/Team/Flags/Bye/
                  Ceiling/PlayoffUp/W15/W16/W17); click a row for flags + a compact
                  note so risk on your own players is visible too.
  6. LIVE BOX     paste a board / Contract-3 JSON to re-render the embedded data.

This mirrors the repo convention (command_center.py -> command_center.html):
the data + template live together in one auditable Python source.
"""

import json
import os
import sys

# --------------------------------------------------------------------------
# EMBEDDED default payload (live_tree.json shape). Replaced unchanged by the
# real engine output (engine/run_live.py -> live_tree.json) at build time; this
# seed only matters if live_tree.json is missing. Kept tiny on purpose.
# --------------------------------------------------------------------------
EMBEDDED_DATA = {
    "state": {
        "pick": 43, "round": 4, "seat": 7,
        "roster": [
            {"name": "Ja'Marr Chase", "pos": "WR", "team": "CIN"},
            {"name": "Bijan Robinson", "pos": "RB", "team": "ATL"},
            {"name": "Brock Bowers", "pos": "TE", "team": "LV"},
        ],
        "counts": {"QB": 0, "RB": 1, "WR": 1, "TE": 1},
        "anchor": "CIN@BAL", "modeled_n": 3, "drafted_n": 3,
    },
    "headline": {
        "take": "Nico Collins", "dTitle": 1.82, "dAdv": 4.61,
        "why": "Elite WR2 anchor at a WR-thin spot; highest blended d at the pick.",
        "stack": "\U0001f517 onslaught w/ C.J. Stroud (QB)",
    },
    "construction": {
        "counts": {"QB": 0, "RB": 1, "WR": 1, "TE": 1},
        "targets": {"QB": "2-3", "RB": "5-6", "WR": "8-9", "TE": "2-3"},
        "anchor": "CIN@BAL", "byes": [9, 12],
    },
    "tree": {
        "label": "Pick 43 (R4)",
        "branches": [
            {"cond": "if Nico Collins (WR) still on board", "take": "Nico Collins",
             "pos": "WR", "team": "HOU", "dTitle": 1.82, "dAdv": 4.61, "dW17": 2.31,
             "playoff_up": 0.61, "reason": "Best blended value; stacks a 2nd alpha WR.",
             "then": None},
        ],
    },
    "board": [
        {"name": "Nico Collins", "pos": "WR", "team": "HOU", "adp": 41.0, "rank": 38,
         "proj": 14.2, "ceiling": 31.0, "ceil_pct": 0.78, "cv": 0.6, "spike": 0.18,
         "bye": 6, "w15": "ARI", "w16": "LV", "w17": "HOU@TEN", "w17rank": 5,
         "adv_pct": 0.8, "value": 3.0, "playoff_up": 0.61,
         "stack": "\U0001f517 onslaught w/ C.J. Stroud (QB)",
         "scouting": "Bullish: alpha target share in a fast-rising HOU passing game; clean WR2 anchor with WR1 upside.",
         "quote": "Collins is the unquestioned alpha in Houston when healthy.",
         "flags": [], "tweet": None,
         "dTitle": 1.82, "dAdv": 4.61, "dW17": 2.31},
        {"name": "Quinshon Judkins", "pos": "RB", "team": "CLE", "adp": 44.0, "rank": 49,
         "proj": 11.8, "ceiling": 24.0, "ceil_pct": 0.62, "cv": 0.71, "spike": 0.12,
         "bye": 9, "w15": "BAL", "w16": "PIT", "w17": "CLE@IND", "w17rank": 18,
         "adv_pct": 0.55, "value": -5.0, "playoff_up": 0.34,
         "stack": "↩ bring-back (CLE@IND)",
         "scouting": "Bearish: real recovery overhang on the role after a serious lower-leg injury.",
         "quote": None,
         "flags": [{"type": "injury", "note": "Dislocated ankle + fractured fibula 12/21/25; recovery concern."}],
         "tweet": None},
    ],
    "roster_detail": [
        {"name": "Ja'Marr Chase", "pos": "WR", "team": "CIN", "adp": 2.0, "rank": 2,
         "proj": 17.0, "ceiling": 38.0, "ceil_pct": 0.97, "cv": 0.55, "spike": 0.2,
         "bye": 12, "w15": "BAL", "w16": "CLE", "w17": "ARI@CIN", "w17rank": 8,
         "adv_pct": 0.95, "value": 0.0, "playoff_up": 0.7,
         "stack": "\U0001f517 onslaught w/ Joe Burrow (QB)",
         "scouting": "Bullish: WR1 overall anchor with league-best ceiling.",
         "quote": None, "flags": [], "tweet": None},
    ],
}

# --------------------------------------------------------------------------
# HTML template. __DATA__ is replaced with the JSON payload. Everything else is
# literal; JS braces are written normally (we use .replace, not .format()).
# --------------------------------------------------------------------------
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Best Ball 2026 - Decision Dashboard</title>
<style>
  :root{
    --bg:#0b0f17; --bg2:#111826; --panel:#151d2c; --panel2:#1b2536;
    --line:#26324a; --line2:#324162;
    --ink:#e8eef9; --ink2:#aab6cf; --ink3:#74829e;
    --accent:#5b9dff; --accent2:#7c5cff;
    --good:#34d399; --goodbg:#0e2a22; --bad:#fb7185; --badbg:#2c1117;
    --warn:#fbbf24; --warnbg:#2a210a;
    --stackbg:#0e2a22; --stackink:#6ee7b7; --stackline:#1c5a45;
    --bringbg:#2a210a; --bringink:#fcd34d; --bringline:#7a5a16;
    --chipbg:#1c2740; --chipink:#bcd0ff;
    --posQB:#f59e0b; --posRB:#34d399; --posWR:#5b9dff; --posTE:#c084fc; --posFLEX:#94a3b8;
    --radius:14px; --shadow:0 10px 30px rgba(0,0,0,.45);
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{
    background:
      radial-gradient(1200px 600px at 80% -10%, #16203400 0%, #0b0f17 60%),
      radial-gradient(900px 500px at -10% 0%, #1a1430 0%, #0b0f17 55%),
      var(--bg);
    color:var(--ink); font-family:var(--sans);
    font-size:14px; line-height:1.45; -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:1320px; margin:0 auto; padding:24px 20px 64px}
  .topbar{display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px; flex-wrap:wrap}
  .brand{display:flex; align-items:center; gap:12px}
  .logo{width:38px;height:38px;border-radius:10px;
    background:linear-gradient(135deg,var(--accent),var(--accent2));
    display:grid;place-items:center;font-weight:800;color:#fff;box-shadow:var(--shadow)}
  .brand h1{font-size:17px;margin:0;letter-spacing:.2px}
  .brand .sub{color:var(--ink3);font-size:12px;margin-top:1px}
  .pill{font-size:11px;color:var(--ink2);background:var(--chipbg);border:1px solid var(--line);
    padding:4px 9px;border-radius:999px}

  /* ---- state header ---- */
  .statecard{background:linear-gradient(180deg,var(--panel),var(--bg2));
    border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px; box-shadow:var(--shadow);
    margin-bottom:16px}
  .stategrid{display:flex; flex-wrap:wrap; gap:18px; align-items:center}
  .kv{display:flex; flex-direction:column; min-width:58px}
  .kv .k{font-size:10.5px; text-transform:uppercase; letter-spacing:.7px; color:var(--ink3)}
  .kv .v{font-size:18px; font-weight:700; font-family:var(--mono)}
  .kv .v small{font-size:11px;color:var(--ink3);font-weight:600}
  .counts{display:flex; gap:8px; flex-wrap:wrap}
  .cnt{display:flex; align-items:center; gap:6px; background:var(--chipbg); border:1px solid var(--line);
    border-radius:10px; padding:5px 9px; font-family:var(--mono); font-size:13px}
  .cnt b{font-weight:700}
  .cnt .tgt{color:var(--ink3); font-size:11px}
  .cnt.below{border-color:var(--bad); background:var(--badbg)}
  .cnt.below b{color:var(--bad)}
  .cnt.met{border-color:#1c5a45}
  .dot{width:9px;height:9px;border-radius:3px;display:inline-block}
  .d-QB{background:var(--posQB)} .d-RB{background:var(--posRB)}
  .d-WR{background:var(--posWR)} .d-TE{background:var(--posTE)} .d-FLEX{background:var(--posFLEX)}
  .anchor{margin-left:auto; text-align:right}
  .anchor .k{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink3)}
  .anchor .v{font-size:14px;font-weight:700;color:var(--warn);font-family:var(--mono)}
  .byes{margin-top:2px}
  .byes .v{font-size:13px;color:var(--ink2);font-family:var(--mono);font-weight:600}
  .modeled{margin-top:12px; padding-top:12px; border-top:1px dashed var(--line); display:flex; flex-wrap:wrap; gap:18px; align-items:flex-start}
  .modeled .lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink3);margin-bottom:4px}
  .modeled .big{font-size:15px;font-weight:700;font-family:var(--mono)}
  .namelist{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
  .nchip{font-size:11.5px;background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px 9px;color:var(--ink2)}
  .nchip.drop{border-color:#5e2330;color:var(--bad)}
  .roster{margin-top:12px; padding-top:12px; border-top:1px dashed var(--line)}
  .roster .lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink3);margin-bottom:7px}
  .rosterchips{display:flex;flex-wrap:wrap;gap:7px}
  .rchip{display:flex;align-items:center;gap:7px;background:var(--panel2);border:1px solid var(--line);
    border-radius:999px;padding:4px 10px 4px 5px;font-size:12.5px}
  .badge{font-size:10px;font-weight:800;color:#06121f;border-radius:6px;padding:2px 6px;letter-spacing:.4px}
  .b-QB{background:var(--posQB)} .b-RB{background:var(--posRB)} .b-WR{background:var(--posWR)}
  .b-TE{background:var(--posTE)} .b-FLEX{background:var(--posFLEX)}
  .rchip .tm{color:var(--ink3);font-family:var(--mono);font-size:11px}

  /* ---- headline ---- */
  .headline{position:relative; overflow:hidden;
    background:
      radial-gradient(600px 200px at 90% -40%, rgba(91,157,255,.18), transparent 60%),
      linear-gradient(180deg,#13203a,#101727);
    border:1px solid var(--line2); border-radius:var(--radius); padding:18px 20px; box-shadow:var(--shadow);
    margin-bottom:18px}
  .headline .tag{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--accent);font-weight:700}
  .hl-row{display:flex; align-items:flex-end; gap:16px; flex-wrap:wrap; margin-top:4px}
  .hl-take{font-size:34px; font-weight:800; letter-spacing:.2px; line-height:1.05}
  .hl-deltas{display:flex; gap:10px; align-items:center; margin-bottom:5px}
  .delta{font-family:var(--mono); font-size:14px; font-weight:700; border-radius:9px; padding:6px 11px;
    border:1px solid var(--line2); display:flex; gap:8px; align-items:baseline; white-space:nowrap}
  .delta .dl{font-size:10px; letter-spacing:.6px; color:var(--ink3); font-family:var(--sans); text-transform:uppercase}
  .pos-good{color:var(--good); background:var(--goodbg); border-color:#1c5a45}
  .pos-bad{color:var(--bad); background:var(--badbg); border-color:#5e2330}
  .hl-why{margin-top:12px; color:var(--ink2); font-size:13.5px; max-width:92ch}
  .hl-why b{color:var(--ink)}

  /* ---- section header ---- */
  .section-h{display:flex; align-items:center; gap:10px; margin:22px 2px 12px}
  .section-h h2{font-size:14px; margin:0; letter-spacing:.3px}
  .section-h .hint{color:var(--ink3); font-size:11.5px}
  .toolrow{margin-left:auto; display:flex; gap:8px; flex-wrap:wrap}
  .btn{font-family:var(--sans); font-size:12px; color:var(--ink); background:var(--panel2);
    border:1px solid var(--line2); border-radius:9px; padding:6px 11px; cursor:pointer}
  .btn:hover{border-color:var(--accent); color:#fff}
  .btn.primary{background:linear-gradient(135deg,var(--accent),var(--accent2)); border:none; color:#fff; font-weight:700}
  .btn.on{background:linear-gradient(135deg,var(--accent),var(--accent2)); border-color:transparent; color:#fff; font-weight:700}
  .btn:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

  /* ---- tree ---- */
  .tree{display:flex; flex-direction:column; gap:10px}
  .branch{background:linear-gradient(180deg,var(--panel),var(--bg2)); border:1px solid var(--line);
    border-radius:12px; box-shadow:0 4px 14px rgba(0,0,0,.28); overflow:hidden}
  .branch.best{border-color:#2d5a3f}
  .branch.best .rank{background:linear-gradient(135deg,var(--good),#0ea371); color:#06231a}
  .bhead{display:flex; align-items:center; gap:12px; padding:13px 14px; cursor:pointer; user-select:none}
  .bhead:hover{background:rgba(91,157,255,.05)}
  .bhead:focus-visible{outline:2px solid var(--accent); outline-offset:-2px; border-radius:12px}
  .rank{flex:none; width:26px;height:26px;border-radius:8px; display:grid;place-items:center;
    font-weight:800; font-size:13px; background:var(--chipbg); color:var(--chipink); border:1px solid var(--line2)}
  .caret{flex:none; width:18px; text-align:center; color:var(--ink3); transition:transform .15s ease;
    font-size:12px; font-family:var(--mono)}
  .branch.open > .bhead .caret{transform:rotate(90deg); color:var(--accent)}
  .bmain{flex:1 1 auto; min-width:0}
  .cond{color:var(--ink2); font-size:12px}
  .cond code{color:var(--chipink); background:var(--chipbg); padding:1px 6px; border-radius:6px;
    font-family:var(--mono); font-size:11.5px}
  .action{display:flex; align-items:center; gap:8px; margin-top:4px; font-weight:700; font-size:15px}
  .action .verb{color:var(--ink3); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.6px}
  .action .tm{color:var(--ink3);font-family:var(--mono);font-size:12px;font-weight:600}
  .bdeltas{flex:none; display:flex; gap:6px; align-items:center; flex-wrap:wrap; justify-content:flex-end}
  .chip{font-family:var(--mono); font-size:12px; font-weight:700; border-radius:8px; padding:4px 8px;
    border:1px solid var(--line2); display:flex; gap:6px; align-items:baseline; white-space:nowrap}
  .chip .cl{font-size:9.5px; letter-spacing:.5px; color:var(--ink3); font-family:var(--sans)}
  .chip.pup{color:var(--ink); background:var(--chipbg)}
  .bbody{display:none; padding:0 14px 14px 52px; border-top:1px solid var(--line)}
  .branch.open > .bbody{display:block}
  .reason{color:var(--ink2); font-size:12.8px; margin:12px 0 0; padding-left:12px; border-left:2px solid var(--line2)}
  .then-wrap{margin-top:14px}
  .then-lbl{display:flex; align-items:center; gap:8px; font-size:11px; text-transform:uppercase; letter-spacing:.7px;
    color:var(--ink3); margin-bottom:8px}
  .then-lbl .arrow{color:var(--accent)}
  .subtree{display:flex; flex-direction:column; gap:8px; padding-left:6px; border-left:2px dashed var(--line2)}
  .subbranch{background:var(--panel2); border:1px solid var(--line); border-radius:10px; overflow:hidden; margin-left:6px}
  .subhead{display:flex; align-items:center; gap:10px; padding:10px 12px; cursor:pointer; user-select:none}
  .subhead:hover{background:rgba(91,157,255,.05)}
  .subhead:focus-visible{outline:2px solid var(--accent); outline-offset:-2px; border-radius:10px}
  .subbody{display:none; padding:0 12px 12px 40px; border-top:1px solid var(--line)}
  .subbranch.open > .subbody{display:block}
  .subbranch.open > .subhead .caret{transform:rotate(90deg); color:var(--accent)}
  .leaf{font-size:11px; color:var(--ink3); margin-top:10px; font-style:italic}

  .empty{color:var(--ink3); padding:30px; text-align:center; border:1px dashed var(--line); border-radius:12px}

  /* ---- data tables (board + roster) ---- */
  .tablecard{background:linear-gradient(180deg,var(--panel),var(--bg2)); border:1px solid var(--line);
    border-radius:var(--radius); box-shadow:var(--shadow); overflow:hidden}
  .tablescroll{overflow-x:auto; max-width:100%}
  table.data{border-collapse:collapse; width:100%; font-size:12.5px}
  table.data th, table.data td{padding:7px 10px; text-align:right; white-space:nowrap; border-bottom:1px solid var(--line)}
  table.data th:first-child, table.data td:first-child{text-align:center}
  table.data th.l, table.data td.l{text-align:left}
  table.data thead th{position:sticky; top:0; z-index:2; background:#0e1626; color:var(--ink2);
    font-size:10.5px; text-transform:uppercase; letter-spacing:.5px; cursor:pointer; user-select:none;
    border-bottom:1px solid var(--line2)}
  table.data thead th:hover{color:#fff; background:#13203a}
  table.data thead th .ar{color:var(--accent); font-family:var(--mono); margin-left:3px}
  table.data thead th[aria-sort="none"] .ar{color:var(--ink3); opacity:.45}
  table.data tbody tr.drow{cursor:pointer}
  table.data tbody tr.drow:hover{background:rgba(91,157,255,.06)}
  table.data tbody tr.intree{background:rgba(124,92,255,.10)}
  table.data tbody tr.intree:hover{background:rgba(124,92,255,.16)}
  table.data tbody tr.intree td:first-child{box-shadow:inset 3px 0 0 var(--accent2)}
  table.data td.player{font-weight:700; color:var(--ink)}
  table.data td.player .star{color:var(--accent2); margin-right:4px; font-size:11px}
  table.data td.tm{color:var(--ink3); font-family:var(--mono)}
  table.data td.num{font-family:var(--mono)}
  .pos-pill{display:inline-block; font-size:10px; font-weight:800; color:#06121f; border-radius:6px; padding:2px 7px; letter-spacing:.4px}
  .p-QB{background:var(--posQB)} .p-RB{background:var(--posRB)} .p-WR{background:var(--posWR)}
  .p-TE{background:var(--posTE)} .p-FLEX{background:var(--posFLEX)}
  .g{color:var(--good)} .r{color:var(--bad)} .mut{color:var(--ink3)}

  /* ---- stack badges + highlighted stack rows ---- */
  .stk{display:inline-flex; align-items:center; gap:3px; font-size:10px; font-weight:700;
    border-radius:6px; padding:2px 6px; margin-left:6px; letter-spacing:.2px; white-space:nowrap;
    vertical-align:middle; line-height:1.3; cursor:help}
  .stk.link{background:var(--stackbg); color:var(--stackink); border:1px solid var(--stackline)}
  .stk.bring{background:var(--bringbg); color:var(--bringink); border:1px solid var(--bringline)}
  /* whole-row subtle highlight when a row builds/extends a stack */
  table.data tbody tr.drow.hasstack{background:rgba(52,211,153,.055)}
  table.data tbody tr.drow.hasstack:hover{background:rgba(52,211,153,.11)}
  table.data tbody tr.drow.hasstack td:first-child{box-shadow:inset 3px 0 0 var(--good)}
  table.data tbody tr.drow.hasstack.bringback{background:rgba(251,191,36,.055)}
  table.data tbody tr.drow.hasstack.bringback:hover{background:rgba(251,191,36,.11)}
  table.data tbody tr.drow.hasstack.bringback td:first-child{box-shadow:inset 3px 0 0 var(--warn)}
  /* a stacked row that is ALSO in the tree keeps the tree accent on top */
  table.data tbody tr.drow.intree.hasstack td:first-child{box-shadow:inset 3px 0 0 var(--accent2)}

  /* note expansion row -> RICH scouting card */
  tr.noterow{display:none}
  tr.noterow.show{display:table-row}
  tr.noterow td{text-align:left; background:#0c1320; border-bottom:1px solid var(--line2)}
  .notebox{padding:8px 4px; color:var(--ink2); font-size:12.5px; line-height:1.6; max-width:130ch}
  .notebox .nlbl{font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink3);margin-right:8px}
  .notebox .nrow{margin:0 0 9px}
  .notebox .nrow:last-child{margin-bottom:0}
  /* stack banner (prominent) at top of the card */
  .stackbanner{display:inline-flex; align-items:center; gap:7px; font-size:12.5px; font-weight:700;
    border-radius:9px; padding:6px 11px; margin-bottom:10px}
  .stackbanner.link{background:var(--stackbg); color:var(--stackink); border:1px solid var(--stackline)}
  .stackbanner.bring{background:var(--bringbg); color:var(--bringink); border:1px solid var(--bringline)}
  .stackbanner .sblbl{font-size:9.5px; letter-spacing:.7px; text-transform:uppercase; opacity:.8; font-weight:800}
  /* flag warning chips */
  .flags{display:flex; flex-wrap:wrap; gap:7px; margin-bottom:4px}
  .fchip{display:inline-flex; align-items:flex-start; gap:6px; border-radius:8px; padding:5px 9px;
    font-size:11.5px; line-height:1.4; max-width:60ch; border:1px solid}
  .fchip .ft{font-size:9px; font-weight:800; letter-spacing:.5px; text-transform:uppercase;
    border-radius:5px; padding:1px 5px; flex:none; margin-top:1px}
  .fchip.danger{background:var(--badbg); color:#ffd9de; border-color:#5e2330}
  .fchip.danger .ft{background:var(--bad); color:#2c1117}
  .fchip.caution{background:var(--warnbg); color:#fde9b8; border-color:#7a5a16}
  .fchip.caution .ft{background:var(--warn); color:#2a210a}
  .scout{color:var(--ink); font-size:13px; line-height:1.6}
  blockquote.quote{margin:0; padding:6px 0 6px 12px; border-left:3px solid var(--line2);
    color:var(--ink2); font-style:italic; font-size:12.5px; line-height:1.55}
  .buzz{color:var(--ink2); font-size:12.5px; line-height:1.55}
  .buzz .nlbl{color:var(--accent)}
  /* NFL-BRAIN block (brain_intel.json — dated SS claims / forward-2026 leans / tweet buzz) */
  .brainrow{margin:10px 0 9px;padding-top:9px;border-top:1px dashed var(--line2)}
  .brainrow .bhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;margin-bottom:7px}
  .brainrow .bhead .nlbl{color:#b3a6ff;margin-right:0}
  .brainrow .bhead .bstat{font-family:var(--mono);font-size:11px;color:var(--ink3)}
  .brainrow .bitem{display:flex;gap:7px;align-items:flex-start;margin:0 0 6px;font-size:12.3px;
    line-height:1.5;color:var(--ink2);max-width:110ch}
  .brainrow .btag{flex:none;font-size:9px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;
    border-radius:5px;padding:2px 6px;margin-top:1px}
  .brainrow .btag.sig{background:rgba(46,160,90,.16);color:#5fd08a;border:1px solid rgba(46,160,90,.4)}
  .brainrow .btag.noi{background:rgba(150,150,160,.12);color:var(--ink3);border:1px solid var(--line2)}
  .brainrow .btag.lean{background:rgba(157,140,255,.14);color:#b3a6ff;border:1px solid rgba(157,140,255,.4)}
  .brainrow .btag.tw{background:rgba(80,150,220,.12);color:#7fb5e8;border:1px solid rgba(80,150,220,.35)}
  .brainrow .bmeta{font-family:var(--mono);font-size:10.5px;color:var(--ink3);white-space:nowrap}
  .brainrow .bgame{color:var(--ink3);font-style:italic}
  .brainrow .bcoach{font-size:11px;color:var(--ink3);margin-top:2px}
  .notebox .nmeta{display:inline-flex;gap:10px 14px;flex-wrap:wrap;margin-top:10px;padding-top:9px;
    border-top:1px dashed var(--line2);font-family:var(--mono);font-size:11.5px;color:var(--ink3)}
  .notebox .nmeta b{color:var(--ink2)}
  /* USAGE / ROLE line */
  .notebox .usage{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px;margin:0 0 9px;
    font-family:var(--mono);font-size:12px;color:var(--ink2)}
  .notebox .usage .urole{font-size:10px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;
    background:var(--chipbg);color:var(--chipink);border:1px solid var(--line2);border-radius:6px;padding:2px 7px}
  .notebox .usage .uval{white-space:nowrap}
  .notebox .usage .uval b{color:var(--ink)}
  .notebox .usage .usep{color:var(--ink3)}
  /* MODEL CARD: wrap-flow of percentile chips, each color-scaled by value */
  .notebox .modelcard{margin:10px 0 0;padding-top:9px;border-top:1px dashed var(--line2)}
  .notebox .modelcard .mclbl{font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink3);
    margin:0 0 7px;font-weight:700}
  .notebox .mchips{display:flex;flex-wrap:wrap;gap:6px}
  .notebox .mchip{display:inline-flex;align-items:center;gap:6px;border-radius:7px;padding:3px 8px;
    font-size:11px;border:1px solid var(--line2);background:var(--panel2);line-height:1.3}
  .notebox .mchip .ml{color:var(--ink2);font-size:10px;text-transform:uppercase;letter-spacing:.4px}
  .notebox .mchip .mv{font-family:var(--mono);font-weight:700;font-size:11.5px;min-width:30px;text-align:right;
    border-radius:5px;padding:1px 5px}
  .notebox .mfoot{margin-top:8px;font-family:var(--mono);font-size:11px;color:var(--ink3)}
  .notebox .mfoot b{color:var(--ink2)}
  /* analyst CONVICTION chip + FILM note */
  .notebox .convchip{display:inline-flex;align-items:center;gap:8px;border-radius:8px;padding:4px 10px;font-size:12px;border:1px solid var(--line2)}
  .notebox .convchip .cvlbl{font-size:9.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;opacity:.85}
  .notebox .convchip .cvscore{font-family:var(--mono);font-weight:800}
  .notebox .convchip .cvmeta{font-family:var(--mono);font-size:10.5px;opacity:.8}
  .notebox .convchip.bull{background:rgba(46,160,90,.14);color:#5fd08a;border-color:rgba(46,160,90,.4)}
  .notebox .convchip.bear{background:rgba(214,69,69,.14);color:#ff8c8c;border-color:rgba(214,69,69,.4)}
  .notebox .convchip.neutral{background:var(--chipbg);color:var(--ink2)}
  .notebox .film{color:var(--ink2);font-size:12.5px;line-height:1.55}
  .notebox .film .nlbl{color:#c9a24b}
  /* tweet feed (auto-ingester) */
  .notebox .tweetfeed{margin:8px 0 0}
  .notebox .tweetfeed .tlist{display:flex;flex-direction:column;gap:6px;margin-top:5px}
  .notebox .tweetfeed .titem{font-size:12px;line-height:1.5;color:var(--ink2);border-left:2px solid var(--line2);padding-left:8px}
  .notebox .tweetfeed .tmeta{font-family:var(--mono);font-size:10.5px;color:#5b9dff}
  /* splits / boom conditions */
  .notebox .splits .sphead{margin-top:4px;font-size:12px}
  .notebox .splits .sptag{font-weight:700;color:var(--ink)}
  .notebox .splits .spfav{color:var(--ink3);font-size:11.5px}
  .notebox .splits .spweeks{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
  .notebox .splits .spwk{font-size:11px;border-radius:6px;padding:2px 8px;border:1px solid var(--line2);font-family:var(--mono)}
  .notebox .splits .spwk b{font-family:inherit}
  .notebox .splits .spwk.fav{background:rgba(46,160,90,.14);color:#5fd08a;border-color:rgba(46,160,90,.4)}
  .notebox .splits .spwk.tough{background:rgba(214,69,69,.14);color:#ff8c8c;border-color:rgba(214,69,69,.4)}
  .notebox .splits .spwk.neu{background:var(--panel2);color:var(--ink2)}
  /* headline stack badge (under the pick) */
  .hl-stack{display:inline-flex; align-items:center; gap:7px; margin-top:11px; font-size:12.5px;
    font-weight:700; border-radius:9px; padding:6px 12px}
  .hl-stack.link{background:var(--stackbg); color:var(--stackink); border:1px solid var(--stackline)}
  .hl-stack.bring{background:var(--bringbg); color:var(--bringink); border:1px solid var(--bringline)}
  .hl-stack .sblbl{font-size:9.5px; letter-spacing:.7px; text-transform:uppercase; opacity:.8; font-weight:800}
  /* roster flags + compact note */
  .rmeta{display:none}
  tr.rmeta.show{display:table-row}
  tr.rmeta td{text-align:left; background:#0c1320; border-bottom:1px solid var(--line2)}
  .rmetabox{padding:7px 4px; color:var(--ink2); font-size:12px; line-height:1.55; max-width:120ch}
  .rmetabox .scout{font-size:12px}
  .rosternote{cursor:pointer}
  table.data tbody tr.rosterrow:hover{background:rgba(91,157,255,.06); cursor:pointer}
  .tablefoot{padding:8px 12px; color:var(--ink3); font-size:11px; border-top:1px solid var(--line); display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px}

  /* ---- live paste ---- */
  .live{margin-top:24px; background:linear-gradient(180deg,var(--panel),var(--bg2)); border:1px solid var(--line);
    border-radius:var(--radius); padding:16px; box-shadow:var(--shadow)}
  .live h2{font-size:14px;margin:0 0 4px}
  .live p{color:var(--ink3); font-size:12px; margin:0 0 10px}
  textarea{width:100%; min-height:120px; resize:vertical; background:#0c1320; color:var(--ink);
    border:1px solid var(--line2); border-radius:10px; padding:11px 12px; font-family:var(--mono); font-size:12.5px;
    line-height:1.5}
  textarea:focus{outline:none; border-color:var(--accent)}
  .live-actions{display:flex; gap:9px; align-items:center; margin-top:10px; flex-wrap:wrap}
  .status{font-size:12px; font-family:var(--mono)}
  .status.ok{color:var(--good)} .status.err{color:var(--bad)} .status.muted{color:var(--ink3)}
  .legend{display:flex; gap:14px; flex-wrap:wrap; margin-top:8px; color:var(--ink3); font-size:11px}
  .legend span{display:flex;align-items:center;gap:5px}
  .sw{width:10px;height:10px;border-radius:3px;display:inline-block}
  footer{margin-top:26px; color:var(--ink3); font-size:11px; text-align:center}
  code.k{font-family:var(--mono)}

  /* ---- STRATEGY PANEL (advisory; separate from grader recommendation) ---- */
  .strat-panel{
    background:linear-gradient(180deg,#0f1e30,#0b1420);
    border:1px solid #2a4a6a; border-radius:var(--radius);
    padding:16px 18px; box-shadow:var(--shadow); margin-bottom:18px;
    border-left:4px solid #3b82f6;
  }
  .strat-panel .sp-header{display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}
  .strat-panel .sp-badge{
    font-size:10px;font-weight:800;letter-spacing:1px;text-transform:uppercase;
    background:#1e3a5f;color:#93c5fd;border:1px solid #2563eb;
    border-radius:6px;padding:3px 8px;
  }
  .strat-panel .sp-advisory{
    font-size:10.5px;color:#64748b;font-style:italic;
    border:1px solid #1e293b;border-radius:6px;padding:2px 8px;
  }
  .strat-panel .sp-slot{font-family:var(--mono);font-size:22px;font-weight:800;color:#93c5fd}
  .strat-panel .sp-slot-lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;color:#64748b}
  /* adherence badge */
  .adh-badge{font-size:11px;font-weight:800;letter-spacing:.6px;padding:4px 10px;border-radius:8px;border:1px solid}
  .adh-badge.ON_PLAN{background:#0e2a22;color:#34d399;border-color:#1c5a45}
  .adh-badge.DRIFTING{background:#2a210a;color:#fbbf24;border-color:#7a5a16}
  .adh-badge.OFF_PLAN{background:#2c1117;color:#fb7185;border-color:#5e2330}
  /* strategy selector tabs */
  .strat-tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
  .strat-tab{font-size:11px;font-weight:700;padding:4px 10px;border-radius:8px;border:1px solid #26324a;
    background:var(--panel2);color:var(--ink2);cursor:default}
  .strat-tab.best{background:#1e3a5f;color:#93c5fd;border-color:#2563eb}
  /* section dividers within the panel */
  .sp-section{margin:14px 0 10px;padding-top:12px;border-top:1px dashed #1e293b}
  .sp-section-lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;color:#64748b;margin-bottom:8px;font-weight:700}
  /* live targets grid */
  .sp-targets{display:flex;flex-direction:column;gap:6px}
  .sp-target{
    display:flex;align-items:center;gap:8px;background:#0c1a2c;
    border:1px solid #1e293b;border-radius:10px;padding:7px 10px;flex-wrap:wrap;
  }
  .sp-target.avail{border-color:#1c5a45}
  .sp-target.unavail{opacity:.45}
  .sp-target .tgt-name{font-weight:700;font-size:13px;flex:1 1 auto}
  .sp-target .tgt-meta{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
  .sp-target .tgt-adp{font-family:var(--mono);font-size:11px;color:#64748b}
  .sp-tgt-chip{font-size:10px;font-weight:700;border-radius:5px;padding:2px 7px;border:1px solid}
  .tgt-prim{background:#1e3a5f;color:#93c5fd;border-color:#2563eb}
  .tgt-pivot{background:#1c2740;color:#bcd0ff;border-color:#26324a}
  .tgt-stack{background:#0e2a22;color:#6ee7b7;border-color:#1c5a45}
  .tgt-syn{background:rgba(124,92,255,.18);color:#a78bfa;border-color:#4c1d95}
  .tgt-unavail{background:#2c1117;color:#fb7185;border-color:#5e2330}
  .tgt-avail{background:#0e2a22;color:#34d399;border-color:#1c5a45}
  .tgt-tier{font-size:10px;font-weight:800;border-radius:5px;padding:2px 6px;border:1px solid #26324a;color:#64748b}
  .tgt-tier.ELITE{background:rgba(251,191,36,.14);color:#fbbf24;border-color:rgba(251,191,36,.4)}
  .tgt-tier.HIGH{background:rgba(91,157,255,.14);color:#93c5fd;border-color:rgba(91,157,255,.4)}
  .tgt-tier.MID{background:#1c2740;color:#bcd0ff;border-color:#26324a}
  .tgt-tier.LOW{background:#1a1a1a;color:#64748b;border-color:#26324a}
  /* stack status */
  .sp-stack-item{background:#0c1a2c;border:1px solid #1e293b;border-radius:10px;padding:8px 12px;margin-bottom:6px}
  .sp-stack-team{font-size:13px;font-weight:800;color:#fbbf24;margin-bottom:4px}
  .sp-stack-row{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0;font-size:11.5px;color:var(--ink2)}
  .sp-stack-row .sp-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:#64748b;min-width:70px}
  .sp-name-chip{background:var(--panel2);border:1px solid #26324a;border-radius:6px;padding:2px 7px;font-size:11px;color:var(--ink2)}
  .sp-name-chip.held{background:#0e2a22;color:#6ee7b7;border-color:#1c5a45}
  .sp-name-chip.avail{background:#1e3a5f;color:#93c5fd;border-color:#2563eb}
  /* checkpoints */
  .sp-cp-item{display:flex;gap:8px;align-items:flex-start;background:#0c1a2c;border:1px solid #1e293b;border-radius:10px;padding:7px 10px;margin-bottom:6px;flex-wrap:wrap}
  .sp-cp-rnd{font-family:var(--mono);font-size:18px;font-weight:800;color:#64748b;min-width:28px}
  .sp-cp-body{flex:1}
  .sp-cp-grid{display:flex;gap:10px;flex-wrap:wrap;margin-top:4px}
  .sp-cp-pos{display:flex;flex-direction:column;align-items:center;gap:2px;background:#111826;border:1px solid #1e293b;border-radius:7px;padding:3px 8px}
  .sp-cp-pos .cp-pos-lbl{font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:#64748b}
  .sp-cp-pos .cp-pos-val{font-family:var(--mono);font-size:13px;font-weight:700}
  .sp-cp-pos.at-risk .cp-pos-val{color:#fbbf24}
  .sp-cp-pos.impossible .cp-pos-val{color:#fb7185}
  .sp-cp-pos.ok .cp-pos-val{color:#34d399}
  /* floor warnings */
  .sp-warn{display:inline-flex;align-items:center;gap:6px;background:#2c1117;border:1px solid #5e2330;
    border-radius:8px;padding:5px 10px;font-size:12px;color:#ffd9de;margin:3px 0}
  /* leverage note */
  .sp-leverage{background:#0f1e30;border:1px solid #1e3a5f;border-radius:10px;padding:10px 14px;
    font-size:12.5px;color:#aab6cf;line-height:1.6;margin-top:4px}
  .sp-leverage .lev-lbl{font-size:10px;font-weight:800;letter-spacing:.7px;text-transform:uppercase;color:#64748b;margin-bottom:5px}
  /* error state */
  .sp-error{color:#fb7185;font-size:12px;padding:12px;background:#2c1117;border:1px solid #5e2330;border-radius:10px}
</style>
</head>
<body>
<div class="wrap">

  <div class="topbar">
    <div class="brand">
      <div class="logo">BB</div>
      <div>
        <h1>Best Ball 2026 - Decision Dashboard</h1>
        <div class="sub">DraftKings best ball - advancement + W15-17 ceiling</div>
      </div>
    </div>
    <div class="pill">live_tree.json renderer - <code class="k">me = rsbathla</code></div>
  </div>

  <!-- 1. draft state header -->
  <div class="statecard" id="stateCard"></div>

  <!-- 1b. STRATEGY panel (advisory — separate from grader) -->
  <div id="strategyPanel"></div>

  <!-- 2. headline pick -->
  <div class="headline" id="headline"></div>

  <!-- 3. decision tree -->
  <div class="section-h">
    <h2>Decision tree</h2>
    <span class="hint">click / Enter / Space to expand a branch - ordered best to fallback</span>
    <div class="toolrow">
      <button class="btn" id="expandAll" type="button">Expand all</button>
      <button class="btn" id="collapseAll" type="button">Collapse all</button>
    </div>
  </div>
  <div class="tree" id="tree" role="tree" aria-label="Pick decision tree"></div>

  <!-- 3b. graded-7: next 7 available by rank, simulated for title + advancement -->
  <div class="section-h"><h2>Top 7 &mdash; graded for title &amp; advancement</h2>
    <span class="hint">the next 7 available by rank, each simulated for &Delta;title / &Delta;advancement (branches above are the value/availability scenarios)</span></div>
  <div id="graded7"></div>

  <!-- 4. candidate board (centerpiece) -->
  <div class="section-h">
    <h2>Candidate board</h2>
    <span class="hint">click a column to sort - click a row for the full scouting card - stack rows highlighted, tree picks accented</span>
    <div class="toolrow" id="boardFilters">
      <button class="btn on" data-pos="ALL" type="button">All</button>
      <button class="btn" data-pos="QB" type="button">QB</button>
      <button class="btn" data-pos="RB" type="button">RB</button>
      <button class="btn" data-pos="WR" type="button">WR</button>
      <button class="btn" data-pos="TE" type="button">TE</button>
    </div>
  </div>
  <div class="tablecard">
    <div class="tablescroll">
      <table class="data" id="boardTable">
        <thead><tr id="boardHead"></tr></thead>
        <tbody id="boardBody"></tbody>
      </table>
    </div>
    <div class="tablefoot">
      <span id="boardCount">-</span>
      <span class="mut">value = ADP - rank (positive = falling to you) &middot; PlayoffUp = W15-17 ceiling overlay (0-1)</span>
    </div>
  </div>

  <!-- 5. my roster panel -->
  <div class="section-h">
    <h2>My roster</h2>
    <span class="hint">my players + W15-17 schedule - Flags column shows risk, click a row for flags + note</span>
  </div>
  <div class="tablecard">
    <div class="tablescroll">
      <table class="data" id="rosterTable">
        <thead><tr id="rosterHead"></tr></thead>
        <tbody id="rosterBody"></tbody>
      </table>
    </div>
    <div class="tablefoot"><span id="rosterCount">-</span></div>
  </div>

  <!-- 6. live paste -->
  <div class="live">
    <h2>Paste a board / Contract-3 JSON (live mode)</h2>
    <p>Paste a live_tree.json object (full payload) or a Contract-3 tree, then Build.
       The renderer consumes the engine's JSON object unchanged - run_live.py output drops straight in.</p>
    <textarea id="board" spellcheck="false" placeholder="Paste a live_tree.json object ({state, headline, tree, board, roster_detail, construction}), a bare decision tree, or raw board text..."></textarea>
    <div class="live-actions">
      <button class="btn primary" id="build" type="button">Build</button>
      <button class="btn" id="loadSample" type="button">Load current JSON</button>
      <button class="btn" id="resetSample" type="button">Reset to embedded</button>
      <span class="status muted" id="status">Showing embedded live payload.</span>
    </div>
    <div class="legend">
      <span><i class="sw" style="background:var(--good)"></i> positive / falling (good)</span>
      <span><i class="sw" style="background:var(--bad)"></i> negative (bad)</span>
      <span><i class="sw" style="background:var(--accent2)"></i> in decision tree</span>
      <span><i class="sw" style="background:var(--stackink)"></i> &#128279; stack (your roster)</span>
      <span><i class="sw" style="background:var(--bringink)"></i> &#8617; bring-back</span>
      <span><i class="sw" style="background:var(--posQB)"></i>QB</span>
      <span><i class="sw" style="background:var(--posRB)"></i>RB</span>
      <span><i class="sw" style="background:var(--posWR)"></i>WR</span>
      <span><i class="sw" style="background:var(--posTE)"></i>TE</span>
    </div>
  </div>

  <footer>Self-contained - no external assets, no custom elements. Render entry: <code class="k">renderDashboard(data)</code>.</footer>
</div>

<script>
/* ====================================================================
   Embedded live payload (live_tree.json shape). Replaced unchanged by
   the real engine run_live.py output in production.
   ==================================================================== */
var EMBEDDED_DATA = __DATA__;
var CURRENT = EMBEDDED_DATA;   /* the payload currently rendered */

/* ---- small DOM + format helpers (no frameworks, no custom elements) ---- */
function el(tag, cls, txt){
  var n = document.createElement(tag);
  if(cls) n.className = cls;
  if(txt !== undefined && txt !== null) n.textContent = txt;
  return n;
}
function isNum(v){ return v !== undefined && v !== null && v !== "" && !isNaN(Number(v)); }
function num(v, d){ d = (d === undefined ? 1 : d); return isNum(v) ? Number(v).toFixed(d) : "-"; }
function pctI(v){ return isNum(v) ? Math.round(Number(v)) : null; }
/* percentile (0-100) -> red(low) -> amber(mid) -> green(high) heat color */
function pctColor(p){
  if(!isNum(p)) return {bg:"transparent", fg:"var(--ink3)"};
  var t = Math.max(0, Math.min(100, Number(p))) / 100;
  var hue = t * 130; // 0=red .. 130=green (amber ~ 55-65)
  return {bg:"hsla(" + hue + ",70%,42%,0.30)", fg:"hsl(" + hue + ",85%,78%)"};
}
/* fraction (0-1) -> "NN%"; null -> null */
function fracPct(v){ return isNum(v) ? Math.round(Number(v) * 100) + "%" : null; }
function fmtDelta(v){
  if(!isNum(v)) return "-";
  return (Number(v) >= 0 ? "+" : "") + Number(v).toFixed(2);
}
function deltaClass(v){ if(!isNum(v)) return ""; return Number(v) >= 0 ? "pos-good" : "pos-bad"; }
function safePos(p){ return (p && /^(QB|RB|WR|TE)$/.test(p)) ? p : "FLEX"; }
function esc(s){ return (s === undefined || s === null) ? "" : String(s); }

/* ---- stack + flag classification helpers ----
   stack strings: "🔗 ..." = builds/extends a stack with my roster (green),
                  "↩ ..."  = bring-back / game stack (amber).            */
function hasStack(s){ return !!(s && String(s).trim()); }
function stackKind(s){
  // 🔗 (U+1F517) -> link;  ↩ (U+21A9) -> bring-back. Fall back to link.
  if(!hasStack(s)) return null;
  var t = String(s);
  if(t.indexOf("↩") !== -1 || /bring-?back/i.test(t)) return "bring";
  return "link";
}
function stackLabel(k){ return k === "bring" ? "Bring-back" : "Stack"; }
/* a flag {type, note}: injury/risk -> red (danger); trap/age/etc -> amber (caution) */
function flagSeverity(type){
  var t = String(type || "").toLowerCase();
  if(/risk|injury|injured|hurt/.test(t)) return "danger";
  return "caution"; // trap / age / contingency / anything else
}
function normFlags(flags){ return Array.isArray(flags) ? flags.filter(function(f){ return f && (f.note || f.type); }) : []; }

/* green<->red gradient for a 0..1 score (playoff_up). Returns an rgb() string. */
function heatColor(v){
  if(!isNum(v)) return "var(--ink3)";
  var t = Math.max(0, Math.min(1, Number(v)));
  // red (251,113,133) -> amber (251,191,36) -> green (52,211,153)
  var r,g,b;
  if(t < 0.5){ var u = t/0.5; r=251; g=Math.round(113+(191-113)*u); b=Math.round(133+(36-133)*u); }
  else { var u2=(t-0.5)/0.5; r=Math.round(251+(52-251)*u2); g=Math.round(191+(211-191)*u2); b=Math.round(36+(153-36)*u2); }
  return "rgb("+r+","+g+","+b+")";
}

/* delta chip used inside branches (label + value, color-coded) */
function deltaChip(label, v){
  var c = el("div", "chip");
  c.classList.add(Number(v) >= 0 ? "pos-good" : "pos-bad");
  c.appendChild(el("span", "cl", label));
  c.appendChild(el("span", null, fmtDelta(v)));
  return c;
}
/* neutral chip (playoff_up etc.) */
function valChip(label, v, color){
  var c = el("div","chip pup");
  c.appendChild(el("span","cl",label));
  var sp = el("span", null, isNum(v) ? num(v,2) : "-");
  if(color) sp.style.color = color;
  c.appendChild(sp);
  return c;
}

/* ====================================================================
   1) DRAFT STATE HEADER
   pick/round/seat + "modeled N of M" (+ untracked/dropped names) + anchor
   + bye list + position counts vs construction targets (red if below).
   ==================================================================== */
function parseTargetLow(t){
  // targets look like "2-3" / "5-6" / "8-9"; lower bound drives the red flag.
  if(t === undefined || t === null) return null;
  var m = String(t).match(/(\d+)/);
  return m ? Number(m[1]) : null;
}
function renderState(state, construction, brainMeta){
  var host = document.getElementById("stateCard");
  host.innerHTML = "";
  if(!state){ host.appendChild(el("div","empty","No state provided.")); return; }
  construction = construction || {};
  var targets = construction.targets || {};
  var byes = construction.byes || [];

  // FIELD-COMPLETENESS warning - a partial board copy means drafted players show as available
  if(state.board_warning){
    var wb = el("div");
    wb.style.cssText = "margin:0 0 12px;padding:10px 14px;border-radius:9px;background:var(--badbg,#3a1a20);"+
      "color:#ffd9de;border:1px solid #5e2330;font-size:12.5px;line-height:1.55;font-weight:600";
    wb.textContent = "⚠ " + String(state.board_warning);
    host.appendChild(wb);
  }

  var grid = el("div","stategrid");
  function kv(k, v){
    var b = el("div","kv");
    b.appendChild(el("div","k",k));
    var vv = el("div","v"); vv.textContent = (v===undefined||v===null ? "-" : String(v));
    b.appendChild(vv);
    return b;
  }
  grid.appendChild(kv("Pick", state.pick));
  grid.appendChild(kv("Round", state.round));
  grid.appendChild(kv("Seat", state.seat));

  // position counts vs targets
  var counts = state.counts || {};
  var cnts = el("div","counts");
  ["QB","RB","WR","TE"].forEach(function(p){
    var have = (counts[p] != null ? counts[p] : 0);
    var tgt = targets[p];
    var low = parseTargetLow(tgt);
    var below = (low !== null && have < low);
    var c = el("div","cnt" + (below ? " below" : (low !== null ? " met" : "")));
    c.appendChild(el("span","dot d-"+p));
    var b = el("b", null, p + " " + have);
    c.appendChild(b);
    if(tgt != null) c.appendChild(el("span","tgt","/ " + tgt));
    cnts.appendChild(c);
  });
  var cwrap = el("div","kv"); cwrap.style.minWidth = "auto";
  cwrap.appendChild(el("div","k","Position counts vs target"));
  cwrap.appendChild(cnts);
  grid.appendChild(cwrap);

  // anchor + byes (right side)
  var rt = el("div","anchor");
  rt.appendChild(el("div","k","Anchor game"));
  rt.appendChild(el("div","v", state.anchor || construction.anchor || "-"));
  var byeWrap = el("div","byes");
  byeWrap.appendChild(el("div","k","Roster byes"));
  byeWrap.appendChild(el("div","v", byes.length ? byes.join(", ") : "-"));
  rt.appendChild(byeWrap);
  grid.appendChild(rt);

  host.appendChild(grid);

  // modeled N of M + untracked / dropped
  var modeled = el("div","modeled");
  var mod = el("div");
  mod.appendChild(el("div","lbl","Modeled"));
  var modeled_n = (state.modeled_n != null ? state.modeled_n : (state.roster ? state.roster.length : 0));
  var drafted_n = (state.drafted_n != null ? state.drafted_n : modeled_n);
  mod.appendChild(el("div","big", modeled_n + " of " + drafted_n + " picks"));
  modeled.appendChild(mod);

  var untracked = state.untracked || [];
  if(untracked.length){
    var ut = el("div");
    ut.appendChild(el("div","lbl","Untracked (not modeled)"));
    var ul = el("div","namelist");
    untracked.forEach(function(n){
      var nm = (typeof n === "string") ? n : (n && n.name ? n.name : String(n));
      ul.appendChild(el("span","nchip", nm));
    });
    ut.appendChild(ul);
    modeled.appendChild(ut);
  }
  var dropped = state.dropped || [];
  if(dropped.length){
    var dp = el("div");
    dp.appendChild(el("div","lbl","Dropped (non-gradeable)"));
    var dl = el("div","namelist");
    dropped.forEach(function(n){
      var nm = (typeof n === "string") ? n : (n && n.name ? n.name : String(n));
      dl.appendChild(el("span","nchip drop", nm));
    });
    dp.appendChild(dl);
    modeled.appendChild(dp);
  }
  // NFL-Brain freshness badge — proves at a glance the intel layer loaded and how current it is
  if(brainMeta && (brainMeta.as_of || brainMeta.matched != null)){
    var bm = el("div");
    bm.appendChild(el("div","lbl","🧠 Brain intel"));
    bm.appendChild(el("div","big", brainMeta.matched != null ? (brainMeta.matched + " players carded") : "loaded"));
    if(brainMeta.as_of){
      var bsm = el("div");
      bsm.style.cssText = "font-size:10px;color:var(--ink3);margin-top:2px;font-family:var(--mono)";
      bsm.textContent = "as of " + String(brainMeta.as_of).slice(0,16).replace("T"," ") + " UTC";
      bm.appendChild(bsm);
    }
    modeled.appendChild(bm);
  }
  host.appendChild(modeled);

  // roster chips
  if(state.roster && state.roster.length){
    var r = el("div","roster");
    r.appendChild(el("div","lbl","My roster (" + state.roster.length + ")"));
    var chips = el("div","rosterchips");
    state.roster.forEach(function(pl){
      var pos = safePos(pl.pos);
      var rc = el("div","rchip");
      rc.appendChild(el("span","badge b-"+pos, pos));
      rc.appendChild(el("span", null, pl.name));
      if(pl.team) rc.appendChild(el("span","tm", pl.team));
      chips.appendChild(rc);
    });
    r.appendChild(chips);
    host.appendChild(r);
  }
}

/* ====================================================================
   2) HEADLINE PICK
   ==================================================================== */
/* look up a player's stack tag from the board (headline carries no stack itself) */
function stackForName(board, name){
  if(!Array.isArray(board) || !name) return null;
  for(var i=0;i<board.length;i++){ if(board[i] && board[i].name === name) return board[i].stack || null; }
  return null;
}
function renderHeadline(h, board){
  var host = document.getElementById("headline");
  host.innerHTML = "";
  if(!h){ host.appendChild(el("div","empty","No headline pick.")); return; }

  host.appendChild(el("div","tag","Headline pick"));
  var row = el("div","hl-row");
  row.appendChild(el("div","hl-take", h.take || "-"));

  var deltas = el("div","hl-deltas");
  function bigDelta(label, v){
    var d = el("div","delta " + deltaClass(v));
    d.appendChild(el("span","dl", label));
    d.appendChild(el("span", null, fmtDelta(v)));
    return d;
  }
  deltas.appendChild(bigDelta("dTitle", h.dTitle));
  deltas.appendChild(bigDelta("dAdv", h.dAdv));
  row.appendChild(deltas);
  host.appendChild(row);

  // stack badge under the pick (rationale visible at the pick) -- from board or headline.stack
  var st = h.stack || stackForName(board, h.take);
  if(hasStack(st)){
    var k = stackKind(st);
    var sb = el("div","hl-stack " + k);
    sb.appendChild(el("span","sblbl", stackLabel(k)));
    sb.appendChild(document.createTextNode(String(st)));
    host.appendChild(sb);
  }

  if(h.why){
    var why = el("div","hl-why");
    why.appendChild(el("b", null, "Why: "));
    why.appendChild(document.createTextNode(h.why));
    host.appendChild(why);
  }
}

/* ====================================================================
   3) DECISION TREE  (collapsible, with nested "then" look-ahead)
   ==================================================================== */
function setOpen(node, open){
  if(open){ node.classList.add("open"); } else { node.classList.remove("open"); }
  var head = node.querySelector(":scope > .bhead, :scope > .subhead");
  if(head) head.setAttribute("aria-expanded", open ? "true" : "false");
}
function toggleNode(node){ setOpen(node, !node.classList.contains("open")); }
function wireKeyToggle(head, node){
  head.addEventListener("click", function(){ toggleNode(node); });
  head.addEventListener("keydown", function(ev){
    if(ev.key === "Enter" || ev.key === " " || ev.key === "Spacebar"){
      ev.preventDefault(); toggleNode(node);
    }
  });
}
function headDeltas(b){
  var deltas = el("div","bdeltas");
  deltas.appendChild(deltaChip("dTitle", b.dTitle));
  deltas.appendChild(deltaChip("dAdv", b.dAdv));
  if(b.dW17 !== undefined && b.dW17 !== null) deltas.appendChild(deltaChip("dW17", b.dW17));
  if(b.playoff_up !== undefined && b.playoff_up !== null)
    deltas.appendChild(valChip("playUp", b.playoff_up, heatColor(b.playoff_up)));
  return deltas;
}
function actionRow(b){
  var action = el("div","action");
  action.appendChild(el("span","verb","take"));
  var pos = safePos(b.pos);
  action.appendChild(el("span","badge b-"+pos, pos));
  action.appendChild(document.createTextNode(" " + (b.take || "-")));
  if(b.team) action.appendChild(el("span","tm", b.team));
  return action;
}
function buildSubBranch(b){
  var node = el("div","subbranch");
  node.setAttribute("role","treeitem");
  var head = el("div","subhead");
  head.setAttribute("tabindex","0");
  head.setAttribute("aria-expanded","false");
  head.appendChild(el("span","caret",">"));
  var main = el("div","bmain");
  var cond = el("div","cond");
  cond.appendChild(el("code", null, b.cond || "scenario"));
  main.appendChild(cond);
  main.appendChild(actionRow(b));
  head.appendChild(main);
  head.appendChild(headDeltas(b));
  node.appendChild(head);

  var body = el("div","subbody");
  if(b.reason) body.appendChild(el("div","reason", b.reason));
  if(b.then && b.then.branches && b.then.branches.length){
    var tw = el("div","then-wrap");
    var lbl = el("div","then-lbl");
    lbl.appendChild(el("span","arrow","then"));
    lbl.appendChild(document.createTextNode(b.then.label || "next pick"));
    tw.appendChild(lbl);
    var st = el("div","subtree");
    b.then.branches.forEach(function(c){ st.appendChild(buildSubBranch(c)); });
    tw.appendChild(st);
    body.appendChild(tw);
  } else {
    body.appendChild(el("div","leaf","leaf - no further look-ahead"));
  }
  node.appendChild(body);
  wireKeyToggle(head, node);
  return node;
}
function buildBranch(b, idx, isBest){
  var node = el("div","branch" + (isBest ? " best" : ""));
  node.setAttribute("role","treeitem");
  var head = el("div","bhead");
  head.setAttribute("tabindex","0");
  head.setAttribute("aria-expanded","false");
  head.appendChild(el("div","rank", String(idx + 1)));
  head.appendChild(el("span","caret",">"));
  var main = el("div","bmain");
  var cond = el("div","cond");
  cond.appendChild(el("code", null, b.cond || "scenario"));
  main.appendChild(cond);
  main.appendChild(actionRow(b));
  head.appendChild(main);
  head.appendChild(headDeltas(b));
  node.appendChild(head);

  var body = el("div","bbody");
  if(b.reason) body.appendChild(el("div","reason", b.reason));
  if(b.then && b.then.branches && b.then.branches.length){
    var tw = el("div","then-wrap");
    var lbl = el("div","then-lbl");
    lbl.appendChild(el("span","arrow","then"));
    lbl.appendChild(document.createTextNode(b.then.label || "next pick"));
    tw.appendChild(lbl);
    var st = el("div","subtree");
    b.then.branches.forEach(function(c){ st.appendChild(buildSubBranch(c)); });
    tw.appendChild(st);
    body.appendChild(tw);
  } else {
    body.appendChild(el("div","leaf","leaf - terminal pick (no look-ahead)"));
  }
  node.appendChild(body);
  wireKeyToggle(head, node);
  return node;
}
function renderTree(tree){
  var host = document.getElementById("tree");
  host.innerHTML = "";
  if(!tree || !tree.branches || !tree.branches.length){
    host.appendChild(el("div","empty","No branches in this tree."));
    return;
  }
  if(tree.label){
    var cap = el("div","section-h"); cap.style.margin = "0 2px 4px";
    var h = el("h2", null, tree.label);
    h.style.fontSize = "12px"; h.style.color = "var(--ink3)"; h.style.fontWeight = "600";
    cap.appendChild(h);
    host.appendChild(cap);
  }
  tree.branches.forEach(function(b, i){ host.appendChild(buildBranch(b, i, i === 0)); });
  var first = host.querySelector(".branch");
  if(first) setOpen(first, true);
}

/* collect the set of player names that appear anywhere in the tree (for board highlight). */
function treeTakeSet(tree){
  var set = {};
  function walk(node){
    if(!node || !node.branches) return;
    node.branches.forEach(function(b){
      if(b.take) set[b.take] = true;
      if(b.then) walk(b.then);
    });
  }
  walk(tree);
  return set;
}

/* ====================================================================
   4) CANDIDATE BOARD  -- sortable + position-filterable table
   ==================================================================== */
/* column spec: key, label, type, decimals, left-align flag */
var BOARD_COLS = [
  {k:"rank",      t:"Rank",  type:"int",   l:false},
  {k:"name",      t:"Player",type:"txt",   l:true},
  {k:"pos",       t:"Pos",   type:"pos",   l:true},
  {k:"team",      t:"Team",  type:"team",  l:true},
  {k:"adp",       t:"ADP",   type:"num", d:1, l:false},
  {k:"value",     t:"Value", type:"value",d:1, l:false},
  {k:"proj",      t:"Proj",  type:"num", d:1, l:false},
  {k:"ceiling",   t:"Ceiling",type:"num",d:1, l:false},
  {k:"ceil_pct",  t:"Ceil%", type:"pct",  l:false},
  {k:"boom_ceil",  t:"Boom%", type:"pct",  l:false},
  {k:"bye",       t:"Bye",   type:"int",  l:false},
  {k:"w15",       t:"W15",   type:"game", l:true},
  {k:"w16",       t:"W16",   type:"game", l:true},
  {k:"w17",       t:"W17",   type:"game", l:true},
  {k:"playoff_up",t:"PlayoffUp",type:"heat",d:2,l:false},
  {k:"dTitle",    t:"dTitle",type:"delta",d:2,l:false},
  {k:"dAdv",      t:"dAdv",  type:"delta",d:2,l:false}
];

var boardState = { rows: [], filter: "ALL", sortK: "rank", sortDir: 1, treeSet: {} };

function buildBoardHead(){
  var tr = document.getElementById("boardHead");
  tr.innerHTML = "";
  BOARD_COLS.forEach(function(c){
    var th = el("th", c.l ? "l" : null);
    th.setAttribute("data-k", c.k);
    th.setAttribute("scope","col");
    th.setAttribute("aria-sort","none");
    th.appendChild(document.createTextNode(c.t));
    th.appendChild(el("span","ar",""));          /* arrow indicator */
    tr.appendChild(th);
  });
}

function cellFor(c, row){
  var v = row[c.k];
  var td;
  if(c.type === "txt"){
    td = el("td","player l");
    if(boardState.treeSet[row.name]){
      var star = el("span","star","*"); star.title = "in decision tree";
      td.appendChild(star);
    }
    td.appendChild(document.createTextNode(esc(v) || "-"));
    if(row.name){ var _cx=el("span","ctxchip","EPA"); _cx.setAttribute("data-ctx-name",row.name); _cx.setAttribute("data-ctx-pos",row.pos||""); td.appendChild(_cx); }
    // compact STACK badge next to the name (green link / amber bring-back)
    if(hasStack(row.stack)){
      var sk = stackKind(row.stack);
      var stk = el("span","stk " + (sk === "bring" ? "bring" : "link"));
      stk.textContent = (sk === "bring" ? "↩" : "🔗") + " " + stackLabel(sk);
      stk.title = String(row.stack);
      td.appendChild(stk);
    }
  } else if(c.type === "pos"){
    td = el("td","l");
    var pos = safePos(v);
    td.appendChild(el("span","pos-pill p-"+pos, pos));
  } else if(c.type === "team"){
    td = el("td","tm l", esc(v) || "-");
  } else if(c.type === "game"){
    td = el("td","l mut", esc(v) || "-");
  } else if(c.type === "pct"){
    td = el("td","num", isNum(v) ? Math.round(Number(v)*100) + "%" : "-");
  } else if(c.type === "int"){
    td = el("td","num", isNum(v) ? String(Math.round(Number(v))) : "-");
  } else if(c.type === "value"){
    td = el("td","num");
    if(isNum(v)){
      td.textContent = (Number(v) >= 0 ? "+" : "") + Number(v).toFixed(c.d || 1);
      td.classList.add(Number(v) >= 0 ? "g" : "r");
    } else td.textContent = "-";
  } else if(c.type === "delta"){
    td = el("td","num");
    if(isNum(v)){
      td.textContent = fmtDelta(v);
      td.classList.add(Number(v) >= 0 ? "g" : "r");
    } else { td.textContent = "-"; td.classList.add("mut"); }
  } else if(c.type === "heat"){
    td = el("td","num");
    if(isNum(v)){ td.textContent = Number(v).toFixed(c.d || 2); td.style.color = heatColor(v); td.style.fontWeight = "700"; }
    else td.textContent = "-";
  } else {
    td = el("td","num", isNum(v) ? Number(v).toFixed(c.d || 1) : (esc(v) || "-"));
  }
  return td;
}

function sortRows(rows){
  var k = boardState.sortK, dir = boardState.sortDir;
  var col = BOARD_COLS.filter(function(c){return c.k===k;})[0] || {type:"num"};
  var numeric = (col.type !== "txt" && col.type !== "pos" && col.type !== "team" && col.type !== "game");
  var copy = rows.slice();
  copy.sort(function(a, b){
    var av = a[k], bv = b[k];
    if(numeric){
      var an = isNum(av) ? Number(av) : null, bn = isNum(bv) ? Number(bv) : null;
      if(an === null && bn === null) return 0;
      if(an === null) return 1;       /* missing always sinks to the bottom */
      if(bn === null) return -1;
      return (an - bn) * dir;
    } else {
      var as = (av === undefined || av === null) ? "" : String(av).toLowerCase();
      var bs = (bv === undefined || bv === null) ? "" : String(bv).toLowerCase();
      if(as < bs) return -1 * dir;
      if(as > bs) return 1 * dir;
      return 0;
    }
  });
  return copy;
}

/* ---- RICH scouting card (board row expansion). Order matters:
   stack banner -> FLAGS (warnings) -> 2026 Outlook -> quote -> Buzz -> metrics. ---- */
function buildScoutCard(row){
  var box = el("div","notebox");

  // 1) stack banner (prominent) if present
  if(hasStack(row.stack)){
    var k = stackKind(row.stack);
    var sb = el("div","stackbanner " + k);
    sb.appendChild(el("span","sblbl", stackLabel(k)));
    sb.appendChild(document.createTextNode(String(row.stack)));
    box.appendChild(sb);
  }

  // 2) FLAGS first as colored warning chips (most important)
  var flags = normFlags(row.flags);
  if(flags.length){
    var fr = el("div","nrow");
    var fwrap = el("div","flags");
    flags.forEach(function(f){
      var sev = flagSeverity(f.type);
      var chip = el("div","fchip " + sev);
      chip.appendChild(el("span","ft", String(f.type || "flag").toUpperCase()));
      chip.appendChild(el("span", null, f.note ? String(f.note) : ""));
      fwrap.appendChild(chip);
    });
    fr.appendChild(fwrap);
    box.appendChild(fr);
  }

  // 2b) analyst CONVICTION (directional consensus + chatter volume)
  if(row.conviction && typeof row.conviction === "object" && row.conviction.score != null){
    var cv = row.conviction, sc = Number(cv.score);
    var dir = sc > 0.15 ? "bull" : (sc < -0.15 ? "bear" : "neutral");
    var arrow = dir === "bull" ? "\u25B2" : (dir === "bear" ? "\u25BC" : "\u25AC");
    var cr = el("div","nrow");
    var cchip = el("div","convchip " + dir);
    cchip.appendChild(el("span","cvlbl","Conviction"));
    cchip.appendChild(el("span","cvscore", arrow + " " + (sc>0?"+":"") + sc.toFixed(2)));
    var cmeta = [];
    if(cv.n_sources != null) cmeta.push(num(cv.n_sources,0) + " sources");
    if(cv.n_tweets != null) cmeta.push(num(cv.n_tweets,0) + " tweets");
    if(cmeta.length) cchip.appendChild(el("span","cvmeta", cmeta.join(" \u00B7 ")));
    cr.appendChild(cchip);
    box.appendChild(cr);
  }

  // 2b2) NFL-BRAIN (dated, sourced vault intel — annotate-only; refreshed daily by brain_export)
  if(row.brain && typeof row.brain === "object"){
    var bz = row.brain;
    var brow = el("div","brainrow");
    var bh = el("div","bhead");
    bh.appendChild(el("span","nlbl","🧠 Brain"));
    var bstats = [];
    if((bz.n_sig||0)+(bz.n_noise||0) > 0) bstats.push("film log " + (bz.n_sig||0) + " Signal / " + (bz.n_noise||0) + " Noise (vault)");
    if(bz.n_tw) bstats.push(bz.n_tw + " tweets" + (bz.n_chart ? " ("+bz.n_chart+" charts)" : ""));
    if(bz.n_src) bstats.push(bz.n_src + " sources");
    if(bstats.length) bh.appendChild(el("span","bstat", bstats.join(" · ")));
    brow.appendChild(bh);
    function bitem(tagCls, tagTxt, body, meta){
      var it = el("div","bitem");
      it.appendChild(el("span","btag " + tagCls, tagTxt));
      var sp = el("span", null, String(body||""));
      it.appendChild(sp);
      if(meta) it.appendChild(el("span","bmeta", meta));
      return it;
    }
    // forward-2026 leans (deep rows carry the array; compact rows carry the single top lean)
    var bfwd = Array.isArray(bz.fwd) && bz.fwd.length ? bz.fwd : (bz.lean ? [bz.lean] : []);
    bfwd.forEach(function(c){
      brow.appendChild(bitem("lean","2026 lean", c.t, c.s ? "["+c.s+"]" : ""));
    });
    (Array.isArray(bz.claims) ? bz.claims : []).forEach(function(c){
      var isSig = String(c.s||"").indexOf("Noise") < 0;
      var it = bitem(isSig ? "sig" : "noi", isSig ? "Signal" : "Noise", c.t, c.s ? "["+c.s+"]" : "");
      if(c.g) it.insertBefore(el("span","bgame","("+c.g+") "), it.lastChild);
      brow.appendChild(it);
    });
    (Array.isArray(bz.tw) ? bz.tw : []).forEach(function(x){
      brow.appendChild(bitem("tw", x.tg || "tweet", x.t, ((x.d||"") + " " + (x.a||"")).trim()));
    });
    (Array.isArray(bz.src26) ? bz.src26 : []).forEach(function(x){
      brow.appendChild(bitem("noi","2026 src", x.t, x.d || ""));
    });
    if(bz.coach) brow.appendChild(el("div","bcoach","🏈 " + String(bz.coach)));
    box.appendChild(brow);
  }

  // 2c) SPLITS / boom conditions (matchup-aware ceiling read)
  if(row.splits && Array.isArray(row.splits.profile) && row.splits.profile.length){
    var sp = row.splits;
    var spr = el("div","nrow splits");
    spr.appendChild(el("span","nlbl","\uD83D\uDCCA Boom conditions"));
    var sh = el("div","sphead");
    sh.appendChild(el("span","sptag", sp.profile.join(" + ")));
    if(Array.isArray(sp.weeks) && sp.weeks.length)
      sh.appendChild(el("span","spfav", " \u00b7 playoffs " + (sp.fav||0) + "/" + sp.weeks.length + " favorable"));
    spr.appendChild(sh);
    if(Array.isArray(sp.weeks) && sp.weeks.length){
      var sw = el("div","spweeks");
      sp.weeks.forEach(function(w){
        var c = el("span","spwk " + String(w.v||"neu").toLowerCase());
        c.appendChild(el("b", null, w.wk + " v" + w.opp + " "));
        c.appendChild(document.createTextNode(String(w.v) + (w.why ? " \u00b7 " + w.why : "")));
        sw.appendChild(c);
      });
      spr.appendChild(sw);
    }
    box.appendChild(spr);
  }

  // 2d) BOOM MODEL marks (updated ceiling model: shrink-adjusted ceiling, QB-stack, FA)
  if(row.boom_badge){
    var br = el("div","nrow");
    br.appendChild(el("span","nlbl","\uD83D\uDE80 Boom model"));
    var bmk = el("span","boommark", String(row.boom_badge));
    if(row.boom_tier === "FA"){
      bmk.style.cssText = "font-family:var(--mono,monospace);font-size:12px;padding:2px 8px;border-radius:5px;background:rgba(200,140,40,.14);color:#e6b36a;border:1px solid rgba(200,140,40,.4)";
    } else {
      bmk.style.cssText = "font-family:var(--mono,monospace);font-size:12px;padding:2px 8px;border-radius:5px;background:rgba(46,160,90,.14);color:#5fd08a;border:1px solid rgba(46,160,90,.35)";
    }
    br.appendChild(bmk);
    box.appendChild(br);
  }

  // 3) scouting take
  if(row.scouting){
    var sr = el("div","nrow");
    sr.appendChild(el("span","nlbl","2026 Outlook"));
    sr.appendChild(el("span","scout", String(row.scouting)));
    box.appendChild(sr);
  } else if(!flags.length){
    box.appendChild(el("div","nrow mut","(no scouting note)"));
  }

  // 4) quote (blockquote / italic)
  if(row.quote){
    var qr = el("div","nrow");
    var bq = el("blockquote","quote", String(row.quote));
    qr.appendChild(bq);
    box.appendChild(qr);
  }

  // 5) buzz (raw tweet-derived color)
  if(row.tweet){
    var br = el("div","nrow buzz");
    br.appendChild(el("span","nlbl","Buzz"));
    br.appendChild(document.createTextNode(String(row.tweet)));
    box.appendChild(br);
  }

  // 5d) TWEET FEED (auto-ingester) - recent analyst tweets, newest first
  if(Array.isArray(row.tweets) && row.tweets.length){
    var tf = el("div","nrow tweetfeed");
    tf.appendChild(el("span","nlbl","\uD83D\uDC26 Tweets" + (row.n_tweets ? " ("+row.n_tweets+")" : "")));
    var tlist = el("div","tlist");
    row.tweets.forEach(function(tw){
      var ti = el("div","titem");
      ti.appendChild(el("span","tmeta", (tw.d||"") + " @" + (tw.h||"") + (tw.l ? " \u2665"+tw.l : "")));
      ti.appendChild(document.createTextNode(" " + String(tw.t||"")));
      tlist.appendChild(ti);
    });
    tf.appendChild(tlist);
    box.appendChild(tf);
  }

  // 5c) FILM note (transcribed video/film scouting)
  if(row.film){
    var flmr = el("div","nrow film");
    flmr.appendChild(el("span","nlbl","\uD83C\uDFAC Film" + (row.n_clips ? " ("+num(row.n_clips,0)+" clips)" : "")));
    flmr.appendChild(document.createTextNode(" " + String(row.film)));
    box.appendChild(flmr);
  }

  // 5b) USAGE / ROLE line (from row.usage). Role decides which template; nulls skipped.
  (function(){
    var u = row.usage;
    if(!u || typeof u !== "object") return;
    var role = (u.role || row.pos || "").toString().toUpperCase();
    var ur = el("div","usage");
    ur.appendChild(el("span","urole", role || "USAGE"));
    var parts = [];
    function part(html){ parts.push(html); }
    function bval(label, val, unit){
      // returns a small span "<b>val</b> label" (unit optional, appended to val)
      if(val === null || val === undefined) return null;
      var s = el("span","uval");
      s.appendChild(el("b", null, String(val) + (unit || "")));
      s.appendChild(document.createTextNode(" " + label));
      return s;
    }
    var segs = [];
    var isRB = role === "RB";
    var isRec = (role === "WR" || role === "TE");
    // Build candidate segments per role; if role is neither, show whatever is non-null.
    if(isRB){
      segs.push(bval("car/g", isNum(u.carry_pg) ? num(u.carry_pg,1) : null));
      segs.push(bval("share", fracPct(u.carry_share)));
      segs.push(bval("ypc", isNum(u.ypc) ? num(u.ypc,1) : null));
      segs.push(bval("tgt", fracPct(u.tgt_share)));
      segs.push(bval("vol cv", isNum(u.cv_carry) ? num(u.cv_carry,2) : null));
    } else if(isRec){
      segs.push(bval("tgt share", fracPct(u.tgt_share)));
      segs.push(bval("ypt", isNum(u.ypt) ? num(u.ypt,1) : null));
      segs.push(bval("catch", fracPct(u.catch_rate)));
      segs.push(bval("vol cv", isNum(u.cv_tgt) ? num(u.cv_tgt,2) : null));
    } else {
      // default: whatever is non-null (covers QB / FLEX / unknown role)
      segs.push(bval("car/g", isNum(u.carry_pg) ? num(u.carry_pg,1) : null));
      segs.push(bval("carry share", fracPct(u.carry_share)));
      segs.push(bval("ypc", isNum(u.ypc) ? num(u.ypc,1) : null));
      segs.push(bval("tgt share", fracPct(u.tgt_share)));
      segs.push(bval("ypt", isNum(u.ypt) ? num(u.ypt,1) : null));
      segs.push(bval("catch", fracPct(u.catch_rate)));
      segs.push(bval("dk/g", isNum(u.dk_pg) ? num(u.dk_pg,1) : null));
    }
    segs = segs.filter(function(s){ return s !== null; });
    segs.forEach(function(s, i){
      if(i > 0) ur.appendChild(el("span","usep","\u00B7"));
      ur.appendChild(s);
    });
    if(segs.length) box.appendChild(ur); // skip the line entirely if nothing to show
  })();

  // 5c) MODEL CARD: compact color-scaled percentile chips + consensus footer (from row.model).
  (function(){
    var mo = row.model;
    if(!mo || typeof mo !== "object") return;
    // ordered (label, percentile-key) for the key signals
    var SIG = [
      ["Value","value_pctl"], ["Ceiling","ceiling_pctl"], ["Spike","spike_pctl"],
      ["Adv","adv_pctl"], ["Run-eff","run_eff_pctl"], ["Rec-eff","rec_eff_pctl"],
      ["Route","route_eff_pctl"], ["Explosive","explosive_pctl"], ["O-line","oline_pctl"],
      ["Matchup","matchup_pctl"], ["Boom","boom_pctl"]
    ];
    var chips = [];
    SIG.forEach(function(pair){
      var v = pctI(mo[pair[1]]);
      if(v === null) return; // skip nulls
      var c = pctColor(v);
      var chip = el("div","mchip");
      chip.appendChild(el("span","ml", pair[0]));
      var mv = el("span","mv", String(v));
      mv.style.background = c.bg;
      mv.style.color = c.fg;
      chip.appendChild(mv);
      chips.push(chip);
    });
    if(!chips.length) return; // nothing modeled -> skip block
    var mc = el("div","modelcard");
    mc.appendChild(el("div","mclbl","Model card"));
    var wrap = el("div","mchips");
    chips.forEach(function(c){ wrap.appendChild(c); });
    mc.appendChild(wrap);
    // one-line footer: "model consensus {N} \u00B7 divergence {N} \u00B7 {N} signals"
    var foot = el("div","mfoot");
    var cons = isNum(mo.consensus) ? num(mo.consensus,1) : "-";
    var divg = isNum(mo.divergence) ? num(mo.divergence,1) : "-";
    var nvot = isNum(mo.n_votes) ? String(Math.round(mo.n_votes)) : "-";
    foot.appendChild(document.createTextNode("model consensus "));
    foot.appendChild(el("b", null, cons));
    foot.appendChild(document.createTextNode(" \u00B7 divergence "));
    foot.appendChild(el("b", null, divg));
    foot.appendChild(document.createTextNode(" \u00B7 "));
    foot.appendChild(el("b", null, nvot));
    foot.appendChild(document.createTextNode(" signals"));
    mc.appendChild(foot);
    box.appendChild(mc);
  })();

  // 6) existing metrics line
  var meta = el("div","nmeta");
  function m(label, val){
    var s = el("span"); s.appendChild(el("b", null, label + " ")); s.appendChild(document.createTextNode(val)); return s;
  }
  meta.appendChild(m("cv", num(row.cv,2)));
  meta.appendChild(m("spike", num(row.spike,2)));
  meta.appendChild(m("adv%", isNum(row.adv_pct)?Math.round(row.adv_pct*100)+"%":"-"));
  meta.appendChild(m("ceiling(p95)", num(row.ceiling,1)));
  meta.appendChild(m("W17 blow-up rank", isNum(row.w17rank)?String(Math.round(row.w17rank)):"-"));
  meta.appendChild(m("playoff_up", num(row.playoff_up,2)));
  box.appendChild(meta);
  return box;
}

function renderBoardBody(){
  var body = document.getElementById("boardBody");
  body.innerHTML = "";
  var rows = boardState.rows;
  if(boardState.filter !== "ALL")
    rows = rows.filter(function(r){ return safePos(r.pos) === boardState.filter; });
  rows = sortRows(rows);

  rows.forEach(function(row, i){
    var tr = el("tr","drow");
    tr.setAttribute("data-exp", "bnote-"+i);
    if(boardState.treeSet[row.name]) tr.classList.add("intree");
    if(hasStack(row.stack)){
      tr.classList.add("hasstack");
      if(stackKind(row.stack) === "bring") tr.classList.add("bringback");
    }
    BOARD_COLS.forEach(function(c){ tr.appendChild(cellFor(c, row)); });
    body.appendChild(tr);

    // hidden RICH scouting card row
    var nr = el("tr","noterow");
    nr.id = "bnote-"+i;
    var td = el("td"); td.setAttribute("colspan", String(BOARD_COLS.length));
    td.appendChild(buildScoutCard(row));
    nr.appendChild(td);
    body.appendChild(nr);
  });

  // header arrows + aria-sort
  var ths = document.querySelectorAll("#boardHead th");
  ths.forEach(function(th){
    var k = th.getAttribute("data-k");
    var ar = th.querySelector(".ar");
    if(k === boardState.sortK){
      th.setAttribute("aria-sort", boardState.sortDir === 1 ? "ascending" : "descending");
      ar.textContent = boardState.sortDir === 1 ? "▲" : "▼";
    } else {
      th.setAttribute("aria-sort","none");
      ar.textContent = "▸";
    }
  });

  document.getElementById("boardCount").textContent =
    rows.length + " of " + boardState.rows.length + " candidates" +
    (boardState.filter === "ALL" ? "" : " (" + boardState.filter + ")");
}

function renderBoard(board, treeSet){
  boardState.rows = Array.isArray(board) ? board.slice() : [];
  boardState.treeSet = treeSet || {};
  buildBoardHead();
  renderBoardBody();
}

/* ====================================================================
   5) MY ROSTER PANEL  -- compact, playoff-week schedule + flags/note
   ==================================================================== */
var ROSTER_COLS = [
  {k:"name",      t:"Player", type:"txt", l:true},
  {k:"pos",       t:"Pos",    type:"pos", l:true},
  {k:"team",      t:"Team",   type:"team",l:true},
  {k:"flags",     t:"Flags",  type:"flagcount", l:false},
  {k:"bye",       t:"Bye",    type:"int", l:false},
  {k:"proj",      t:"Proj",   type:"num", d:1, l:false},
  {k:"ceiling",   t:"Ceiling",type:"num", d:1, l:false},
  {k:"playoff_up",t:"PlayoffUp",type:"heat",d:2,l:false},
  {k:"w15",       t:"W15",    type:"game",l:true},
  {k:"w16",       t:"W16",    type:"game",l:true},
  {k:"w17",       t:"W17",    type:"game",l:true}
];
/* compact flag indicator cell for the roster table (a chip + count) */
function flagCountCell(row){
  var flags = normFlags(row.flags);
  var td = el("td","num");
  if(!flags.length){ td.textContent = "-"; td.classList.add("mut"); return td; }
  var anyDanger = flags.some(function(f){ return flagSeverity(f.type) === "danger"; });
  var chip = el("span","fchip " + (anyDanger ? "danger" : "caution"));
  chip.style.padding = "1px 7px";
  chip.appendChild(el("span","ft", String(flags[0].type || "flag").toUpperCase()));
  if(flags.length > 1) chip.appendChild(el("span", null, "+" + (flags.length - 1)));
  chip.title = flags.map(function(f){ return f.type + ": " + (f.note||""); }).join("  |  ");
  td.appendChild(chip);
  return td;
}
/* compact roster meta row: stack + flags + scouting (expandable) */
function buildRosterMeta(row){
  var box = el("div","rmetabox");
  if(hasStack(row.stack)){
    var k = stackKind(row.stack);
    var sb = el("div","stackbanner " + k); sb.style.marginBottom = "8px";
    sb.appendChild(el("span","sblbl", stackLabel(k)));
    sb.appendChild(document.createTextNode(String(row.stack)));
    box.appendChild(sb);
  }
  var flags = normFlags(row.flags);
  if(flags.length){
    var fwrap = el("div","flags"); fwrap.style.marginBottom = "8px";
    flags.forEach(function(f){
      var sev = flagSeverity(f.type);
      var chip = el("div","fchip " + sev);
      chip.appendChild(el("span","ft", String(f.type || "flag").toUpperCase()));
      chip.appendChild(el("span", null, f.note ? String(f.note) : ""));
      fwrap.appendChild(chip);
    });
    box.appendChild(fwrap);
  }
  if(row.scouting){
    var sr = el("div","nrow");
    sr.appendChild(el("span","nlbl","2026 Outlook"));
    sr.appendChild(el("span","scout", String(row.scouting)));
    box.appendChild(sr);
  }
  if(!hasStack(row.stack) && !flags.length && !row.scouting){
    box.appendChild(el("div","mut","(no notes)"));
  }
  return box;
}
function cellForRoster(c, row){
  if(c.type === "flagcount") return flagCountCell(row);
  return cellFor(c, row);
}
function renderRoster(detail){
  var head = document.getElementById("rosterHead");
  var body = document.getElementById("rosterBody");
  head.innerHTML = ""; body.innerHTML = "";
  ROSTER_COLS.forEach(function(c){
    var th = el("th", c.l ? "l" : null, c.t);
    th.setAttribute("scope","col");
    head.appendChild(th);
  });
  var rows = Array.isArray(detail) ? detail : [];
  if(!rows.length){
    var tr = el("tr"); var td = el("td","mut"); td.setAttribute("colspan", String(ROSTER_COLS.length));
    td.style.textAlign = "center"; td.textContent = "No roster detail.";
    tr.appendChild(td); body.appendChild(tr);
    document.getElementById("rosterCount").textContent = "0 players";
    return;
  }
  rows.forEach(function(row, i){
    var tr = el("tr","rosterrow");
    tr.setAttribute("data-exp", "rnote-"+i);
    ROSTER_COLS.forEach(function(c){ tr.appendChild(cellForRoster(c, row)); });
    body.appendChild(tr);

    // hidden compact note row (stack + flags + scouting)
    var nr = el("tr","rmeta");
    nr.id = "rnote-"+i;
    var ntd = el("td"); ntd.setAttribute("colspan", String(ROSTER_COLS.length));
    ntd.appendChild(buildRosterMeta(row));
    nr.appendChild(ntd);
    body.appendChild(nr);
  });
  document.getElementById("rosterCount").textContent =
    rows.length + " players - click a row for flags + note";
}

/* ====================================================================
   STRATEGY PANEL  (advisory -- never alters grader recommendation)
   Renders data.strategy (strategy_panel from engine/strategy_live.py).
   ==================================================================== */
function renderStrategy(sp){
  var host = document.getElementById("strategyPanel");
  if(!host) return;
  host.innerHTML = "";
  if(!sp){ return; }  /* no strategy key at all -> silent */

  var panel = el("div","strat-panel");

  /* ---- header row ---- */
  var hdr = el("div","sp-header");
  var badge = el("span","sp-badge","STRATEGY");
  var advisory = el("span","sp-advisory","advisory panel  —  does not alter grader");
  hdr.appendChild(badge);

  if(sp.error && !sp.slot_detected){
    hdr.appendChild(el("span","sp-advisory","Slot undetectable — " + esc(sp.error)));
    panel.appendChild(hdr);
    host.appendChild(panel);
    return;
  }
  if(sp.error){
    hdr.appendChild(advisory);
    panel.appendChild(hdr);
    var err = el("div","sp-error","Strategy data unavailable: " + esc(sp.error));
    panel.appendChild(err);
    host.appendChild(panel);
    return;
  }

  /* slot */
  var slotWrap = el("div","kv");
  slotWrap.appendChild(el("div","sp-slot-lbl","Draft Slot"));
  slotWrap.appendChild(el("div","sp-slot","S" + (sp.slot || "?")));
  hdr.appendChild(slotWrap);
  hdr.appendChild(advisory);

  /* best-fit adherence */
  var bf = sp.best_fit || {};
  if(bf.id){
    var adh = bf.adherence || "OFF PLAN";
    var adhKey = adh.replace(/\s+/g,"_");
    var adhBadge = el("span","adh-badge " + adhKey, adh);
    hdr.appendChild(adhBadge);
    var bfName = el("span",null);
    bfName.style.cssText = "font-size:12px;font-weight:700;color:#93c5fd;";
    bfName.textContent = bf.id + " — " + (bf.name||"").split(",")[0];
    hdr.appendChild(bfName);
  }
  panel.appendChild(hdr);

  /* ---- strategy tabs ---- */
  if(sp.strategies && sp.strategies.length){
    var tabs = el("div","strat-tabs");
    sp.strategies.forEach(function(s){
      var isBest = bf && s.id === bf.id;
      var tab = el("div","strat-tab" + (isBest?" best":""));
      tab.textContent = s.id + " (" + (s.score||0).toFixed(1) + " — " + (s.adherence||"") + ")";
      tabs.appendChild(tab);
    });
    panel.appendChild(tabs);
  }

  /* ---- best-fit thesis ---- */
  if(bf.thesis){
    var th = el("div");
    th.style.cssText = "font-size:12px;color:#64748b;font-style:italic;margin-bottom:10px;";
    th.textContent = bf.thesis + (bf.thesis.length >= 250 ? "..." : "");
    panel.appendChild(th);
  }

  /* ---- live targets ---- */
  if(sp.live_targets && sp.live_targets.length){
    var sec = el("div","sp-section");
    var secLbl = el("div","sp-section-lbl","Live Targets — this round");
    sec.appendChild(secLbl);
    var tgtList = el("div","sp-targets");
    sp.live_targets.forEach(function(t){
      var row = el("div","sp-target" + (t.available?" avail":" unavail"));
      /* availability badge */
      var avBadge = el("span","sp-tgt-chip " + (t.available?"tgt-avail":"tgt-unavail"),
                       t.available ? "✓ AVAIL" : "× GONE");
      row.appendChild(avBadge);
      /* primary/pivot */
      row.appendChild(el("span","sp-tgt-chip " + (t.is_primary?"tgt-prim":"tgt-pivot"),
                         t.is_primary ? "PRIMARY" : "PIVOT"));
      /* stack pick */
      if(t.stack_pick) row.appendChild(el("span","sp-tgt-chip tgt-stack","STACK"));
      /* synergy */
      if(t.synergy) row.appendChild(el("span","sp-tgt-chip tgt-syn","SYNERGY"));
      /* name */
      var nm = el("span","tgt-name", t.name);
      row.appendChild(nm);
      /* meta */
      var meta = el("div","tgt-meta");
      if(t.pos){
        var posPill = el("span","pos-pill p-" + (t.pos||"FLEX"), t.pos||"");
        meta.appendChild(posPill);
      }
      if(t.team) meta.appendChild(el("span","tgt-adp", t.team));
      if(t.adp != null) meta.appendChild(el("span","tgt-adp", "ADP " + Number(t.adp).toFixed(0)));
      if(t.tier) meta.appendChild(el("span","tgt-tier " + esc(t.tier), t.tier));
      row.appendChild(meta);
      tgtList.appendChild(row);
    });
    sec.appendChild(tgtList);
    panel.appendChild(sec);
  }

  /* ---- stack status ---- */
  if(sp.stack_status && sp.stack_status.length){
    var ss = el("div","sp-section");
    ss.appendChild(el("div","sp-section-lbl","Stack Status"));
    sp.stack_status.forEach(function(st){
      var item = el("div","sp-stack-item");
      var teamHdr = el("div","sp-stack-team");
      teamHdr.textContent = st.team + " — " + (st.tier||"?") + (st.ceiling_score!=null ? " (" + Math.round(st.ceiling_score) + ")" : "");
      item.appendChild(teamHdr);
      function nameChips(names, cls){
        var row = el("div","sp-stack-row");
        names.forEach(function(n){
          row.appendChild(el("span","sp-name-chip " + (cls||""), n));
        });
        return row;
      }
      if(st.held && st.held.length){
        var heldRow = el("div","sp-stack-row");
        heldRow.appendChild(el("span","sp-lbl","Held"));
        st.held.forEach(function(n){ heldRow.appendChild(el("span","sp-name-chip held", n)); });
        item.appendChild(heldRow);
      }
      if(st.available_remaining && st.available_remaining.length){
        var remRow = el("div","sp-stack-row");
        remRow.appendChild(el("span","sp-lbl","Available"));
        st.available_remaining.forEach(function(n){ remRow.appendChild(el("span","sp-name-chip avail", n)); });
        item.appendChild(remRow);
      } else if(st.remaining && st.remaining.length){
        var remRow2 = el("div","sp-stack-row");
        remRow2.appendChild(el("span","sp-lbl","Remaining"));
        st.remaining.forEach(function(n){ remRow2.appendChild(el("span","sp-name-chip", n)); });
        item.appendChild(remRow2);
      }
      if(st.bringbacks_available && st.bringbacks_available.length){
        var bbRow = el("div","sp-stack-row");
        bbRow.appendChild(el("span","sp-lbl","Bring-backs"));
        st.bringbacks_available.slice(0,3).forEach(function(b){
          bbRow.appendChild(el("span","sp-name-chip avail", b.name + (b.adp?" (ADP "+Math.round(b.adp)+")" : "")));
        });
        item.appendChild(bbRow);
      }
      ss.appendChild(item);
    });
    panel.appendChild(ss);
  }

  /* ---- checkpoint tracker ---- */
  if(sp.checkpoints && sp.checkpoints.length){
    var cpsec = el("div","sp-section");
    cpsec.appendChild(el("div","sp-section-lbl","Checkpoint Tracker (upcoming)"));
    sp.checkpoints.slice(0,3).forEach(function(cp){
      var item = el("div","sp-cp-item");
      var rndEl = el("div","sp-cp-rnd","R" + cp.round);
      item.appendChild(rndEl);
      var body = el("div","sp-cp-body");
      if(cp.impossible && cp.impossible.length){
        var impEl = el("div");
        impEl.style.cssText = "font-size:11px;color:#fb7185;margin-bottom:4px;";
        impEl.textContent = "IMPOSSIBLE: " + cp.impossible.join(", ");
        body.appendChild(impEl);
      } else if(cp.at_risk && cp.at_risk.length){
        var riskEl = el("div");
        riskEl.style.cssText = "font-size:11px;color:#fbbf24;margin-bottom:4px;";
        riskEl.textContent = "AT RISK: " + cp.at_risk.join(", ");
        body.appendChild(riskEl);
      }
      var grid = el("div","sp-cp-grid");
      ["QB","RB","WR","TE"].forEach(function(pos){
        var cur = (cp.current||{})[pos] || 0;
        var tgt = (cp.target||{})[pos] || 0;
        var gap = (cp.gaps||{})[pos];
        var posEl = el("div","sp-cp-pos");
        if(cp.impossible && cp.impossible.indexOf(pos) !== -1){
          posEl.classList.add("impossible");
        } else if(cp.at_risk && cp.at_risk.indexOf(pos) !== -1){
          posEl.classList.add("at-risk");
        } else {
          posEl.classList.add("ok");
        }
        posEl.appendChild(el("span","cp-pos-lbl", pos));
        posEl.appendChild(el("span","cp-pos-val", cur + "/" + tgt));
        grid.appendChild(posEl);
      });
      body.appendChild(grid);
      var rrEl = el("div");
      rrEl.style.cssText = "font-size:10.5px;color:#64748b;margin-top:4px;";
      rrEl.textContent = cp.rounds_remaining + " rounds to checkpoint";
      body.appendChild(rrEl);
      item.appendChild(body);
      cpsec.appendChild(item);
    });
    panel.appendChild(cpsec);
  }

  /* ---- floor warnings ---- */
  if(sp.floor_warnings && sp.floor_warnings.length){
    var fw = el("div","sp-section");
    fw.appendChild(el("div","sp-section-lbl","Floor Warnings"));
    sp.floor_warnings.forEach(function(w){
      fw.appendChild(el("div","sp-warn", "⚠️ " + w));
    });
    panel.appendChild(fw);
  }

  /* ---- score breakdown ---- */
  if(bf.score_breakdown && bf.score_breakdown !== "No roster yet"){
    var bd = el("div","sp-section");
    bd.appendChild(el("div","sp-section-lbl","Fit Breakdown"));
    var bdTxt = el("div");
    bdTxt.style.cssText = "font-size:11.5px;color:#64748b;";
    bdTxt.textContent = bf.score_breakdown;
    bd.appendChild(bdTxt);
    panel.appendChild(bd);
  }

  /* ---- leverage note ---- */
  if(sp.leverage_pivot){
    var lsec = el("div","sp-section");
    lsec.appendChild(el("div","sp-section-lbl","Leverage / De-chalk"));
    var lev = el("div","sp-leverage");
    lev.textContent = sp.leverage_pivot;
    lsec.appendChild(lev);
    panel.appendChild(lsec);
  }

  host.appendChild(panel);
}

/* ====================================================================
   SINGLE ENTRY POINT. Consumes the live_tree.json object unchanged:
   { state, headline, tree, board, roster_detail, construction }
   ==================================================================== */
function renderGraded7(g){
  var host=document.getElementById("graded7"); if(!host) return;
  if(!g||!g.length){host.innerHTML='<span class="hint">no graded-7 in this payload</span>'; return;}
  var rows=g.map(function(x){
    var dt=(x.dtitle==null)?'':((x.dtitle>0?'+':'')+x.dtitle);
    var da=(x.dadv==null)?'':((x.dadv>0?'+':'')+x.dadv);
    var dtc=(x.dtitle>0)?'var(--good)':'var(--bad)', dac=(x.dadv>0)?'var(--good)':'var(--bad)';
    return '<tr><td class="num">'+esc(x.rank)+'</td><td style="text-align:left"><b>'+esc(x.name)+'</b></td>'
      +'<td>'+esc(x.pos)+'/'+esc(x.team)+'</td><td class="num">'+(x.adp==null?'':Math.round(x.adp))+'</td>'
      +'<td class="num" style="color:'+dtc+';font-weight:700">'+dt+'</td>'
      +'<td class="num" style="color:'+dac+';font-weight:700">'+da+'</td>'
      +'<td class="num">'+(x.playoff_up==null?'':x.playoff_up)+'</td></tr>';
  }).join('');
  host.innerHTML='<table class="data"><thead><tr><th>Rank</th><th style="text-align:left">Player</th><th>Pos/Tm</th><th>ADP</th><th>\u0394Title</th><th>\u0394Adv</th><th>PO\u2191</th></tr></thead><tbody>'+rows+'</tbody></table>';
}
function renderDashboard(data){
  data = data || {};
  CURRENT = data;
  var treeSet = treeTakeSet(data.tree);
  renderState(data.state, data.construction, data.brain_meta);
  renderStrategy(data.strategy);
  renderHeadline(data.headline, data.board);
  renderTree(data.tree);
  renderGraded7(data.graded7);
  renderBoard(data.board, treeSet);
  renderRoster(data.roster_detail);
}

/* ---- expand / collapse all (tree) ---- */
function allNodes(){ return document.querySelectorAll("#tree .branch, #tree .subbranch"); }
function setStatus(msg, kind){
  var s = document.getElementById("status");
  s.textContent = msg; s.className = "status " + (kind || "muted");
}

/* ---- live: build from textarea ---- */
function buildFromText(){
  var txt = document.getElementById("board").value.trim();
  if(!txt){
    renderDashboard(EMBEDDED_DATA);
    setStatus("Empty input - rendered embedded payload.", "muted");
    return;
  }
  var looksJson = (txt[0] === "{" || txt[0] === "[");
  if(looksJson){
    var obj;
    try { obj = JSON.parse(txt); }
    catch(e){ setStatus("JSON parse error: " + e.message, "err"); return; }
    if(obj && (obj.tree || obj.board || obj.headline || obj.state)){
      var data = obj.tree ? obj : (obj.branches ? {tree: obj} : obj);
      renderDashboard(data);
      var nb = (data.board && data.board.length) || 0;
      var ntb = (data.tree && data.tree.branches && data.tree.branches.length) || 0;
      setStatus("Rendered pasted payload (" + ntb + " branches, " + nb + " candidates).", "ok");
      return;
    }
    if(obj && obj.branches){
      renderDashboard({tree: obj});
      setStatus("Rendered pasted bare tree (" + (obj.branches.length) + " branches).", "ok");
      return;
    }
    setStatus("Parsed JSON but no recognised keys (state/headline/tree/board).", "err");
    return;
  }
  renderDashboard(EMBEDDED_DATA);
  var lines = txt.split(/\r?\n/).filter(function(l){return l.trim();}).length;
  setStatus("Board received (" + lines + " lines). Engine wiring pending - showing embedded payload.", "ok");
}

/* ---- boot ---- */
document.addEventListener("DOMContentLoaded", function(){
  renderDashboard(EMBEDDED_DATA);

  document.getElementById("expandAll").addEventListener("click", function(){
    allNodes().forEach(function(n){ setOpen(n, true); });
  });
  document.getElementById("collapseAll").addEventListener("click", function(){
    allNodes().forEach(function(n){ setOpen(n, false); });
  });

  document.getElementById("boardHead").addEventListener("click", function(e){
    var th = e.target.closest ? e.target.closest("th") : null;
    if(!th) return;
    var k = th.getAttribute("data-k");
    if(!k) return;
    if(boardState.sortK === k) boardState.sortDir *= -1;
    else { boardState.sortK = k; boardState.sortDir = 1; }
    renderBoardBody();
  });

  document.getElementById("boardBody").addEventListener("click", function(e){
    var row = e.target.closest ? e.target.closest("tr.drow") : null;
    if(!row) return;
    var id = row.getAttribute("data-exp");
    var nr = document.getElementById(id);
    if(nr) nr.classList.toggle("show");
  });

  document.getElementById("rosterBody").addEventListener("click", function(e){
    var row = e.target.closest ? e.target.closest("tr.rosterrow") : null;
    if(!row) return;
    var id = row.getAttribute("data-exp");
    var nr = document.getElementById(id);
    if(nr) nr.classList.toggle("show");
  });

  document.getElementById("boardFilters").addEventListener("click", function(e){
    var btn = e.target.closest ? e.target.closest("button[data-pos]") : null;
    if(!btn) return;
    boardState.filter = btn.getAttribute("data-pos");
    var btns = document.querySelectorAll("#boardFilters button[data-pos]");
    btns.forEach(function(b){ b.classList.toggle("on", b === btn); });
    renderBoardBody();
  });

  document.getElementById("build").addEventListener("click", buildFromText);
  document.getElementById("resetSample").addEventListener("click", function(){
    document.getElementById("board").value = "";
    renderDashboard(EMBEDDED_DATA);
    setStatus("Reset to embedded payload.", "muted");
  });
  document.getElementById("loadSample").addEventListener("click", function(){
    document.getElementById("board").value = JSON.stringify(CURRENT, null, 2);
    setStatus("Current JSON loaded into the box - press Build.", "muted");
  });
});

/* expose for headless/jsdom validation + future engine wiring */
if (typeof window !== "undefined") {
  window.renderDashboard = renderDashboard;
  window.renderTree = renderTree;
  window.renderBoard = renderBoard;
  window.renderRoster = renderRoster;
  window.renderHeadline = renderHeadline;
  window.buildScoutCard = buildScoutCard;
  window.buildFromText = buildFromText;
  window.boardState = boardState;
  window.EMBEDDED_DATA = EMBEDDED_DATA;
}
</script>
</body>
</html>
"""


def write_dashboard(data, out, src="in-memory"):
    """Render + write the dashboard from an in-memory data dict (NO file round-trip).
    Compact embedded payload + freshness banner + verify-retry write. Returns bytes written."""
    import time
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)   # compact embedded data
    html = HTML.replace("__DATA__", payload)
    nb = len(data.get("board", []) or [])
    # Honest freshness banner (C2 fix 2026-07): NEVER unconditionally green. Red when the board is
    # field-incomplete, amber when we can't vouch for recency (no capture stamp, or stale), green only
    # when complete AND recent. captured_at is stamped by run_live at board-capture time (travels with
    # the payload, so a re-render later shows real age). Known-bad cases that must NOT be green:
    # empty board, board_warning present, captured_at missing, captured_at older than STALE_MIN.
    STALE_MIN = 20
    _st = (data.get("state") or {})
    _warn = _st.get("board_warning")
    _cap = _st.get("captured_at")
    _age = (time.time() - _cap) / 60.0 if isinstance(_cap, (int, float)) else None
    if nb == 0 or _warn:                                  # RED \u2014 incomplete / no board
        _bg, _c, _br = "rgba(210,60,60,.16)", "#ff8a8a", "rgba(210,60,60,.55)"
        _txt = "\u26a0 FIELD INCOMPLETE \u2014 do not trust picks \u00b7 {:,} players".format(nb)
    elif _age is None:                                    # AMBER \u2014 no capture timestamp to vouch for
        _bg, _c, _br = "rgba(210,160,60,.15)", "#ffcf7a", "rgba(210,160,60,.5)"
        _txt = "\u26a0 age unverified (no capture stamp) \u00b7 {:,} players".format(nb)
    elif _age > STALE_MIN:                                # AMBER \u2014 stale board
        _bg, _c, _br = "rgba(210,160,60,.15)", "#ffcf7a", "rgba(210,160,60,.5)"
        _txt = "\u26a0 board {:.0f} min old \u2014 re-capture \u00b7 {:,} players".format(_age, nb)
    else:                                                 # GREEN \u2014 complete AND recent
        _bg, _c, _br = "rgba(46,160,90,.14)", "#5fd08a", "rgba(46,160,90,.45)"
        _txt = "\u2713 live \u00b7 complete \u00b7 {:,} players \u00b7 {:.0f} min old".format(nb, _age)
    _banner = ('<div class="pill" style="background:{};color:{};border:1px solid {}">{}</div>').format(_bg, _c, _br, _txt)
    html = html.replace('<div class="pill">live_tree.json renderer',
                        _banner + '<div class="pill">live_tree.json renderer', 1)
    import ctx_panel; html = ctx_panel.inject(html)   # 4-layer NFL Pro EPA drilldown (click the EPA chip on a player row)
    for attempt in range(1, 4):
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(html); f.flush(); os.fsync(f.fileno())
        with open(tmp, encoding="utf-8") as f:
            back = f.read()
        if len(back) == len(html) and back.rstrip().endswith("</html>"):
            os.replace(tmp, out)
            print("[dashboard write OK v3] %d bytes, </html> verified (attempt %d) [%s]" % (len(html), attempt, src))
            return len(html)
        print("[dashboard write retry %d] read-back %d/%d bytes - retrying" % (attempt, len(back), len(html)))
        time.sleep(0.3)
    raise SystemExit("!! dashboard write failed after 3 tries; previous file left intact.")


def inject_boom(data, here):
    """Join the boom model's per-player marks (ceiling %, best-week label, stack, FA) onto
    every board/candidate/roster player so the draft tool shows the same ceiling truth as the
    Player Explorer. Source: boom/boom_marks.json (built by build_boom_marks.py)."""
    import re
    mp = os.path.join(here, "boom", "boom_marks.json")
    if not os.path.exists(mp):
        return 0
    BM = json.load(open(mp, encoding="utf-8"))
    def fn(n):
        n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
        return " ".join(n.replace(".", "").replace("'", "").replace("-", " ").split())
    hit = 0
    for key in ("board", "candidates", "roster_detail"):
        for row in (data.get(key) or []):
            nm = row.get("name")
            bm = BM.get(fn(nm)) if nm else None
            if bm:
                row["boom_ceil"] = (bm["ceiling_pct"] or 0) / 100.0
                row["boom_badge"] = bm["badge"]; row["boom_tier"] = bm["tier"]
                row["boom_lab"] = bm["best_lab"]; row["boom_stack"] = bm["stack"]; row["boom_fa"] = bm["fa"]
                hit += 1
    return hit


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "decision_dashboard.html")
    live = os.path.join(here, "engine", "live_tree.json")
    data = EMBEDDED_DATA; src = "EMBEDDED sample"
    if os.path.exists(live):
        import time
        # this filesystem can lag the TAIL of a freshly-written large file; retry the read before giving up
        for attempt in range(6):
            try:
                with open(live, encoding="utf-8") as f:
                    data = json.load(f)
                src = "live_tree.json"; break
            except (json.JSONDecodeError, ValueError) as e:
                if attempt == 5:
                    sys.stderr.write(
                        "\nERROR: %s unreadable after retries (%s).\n"
                        "The dashboard was NOT updated (kept the previous file).\n"
                        "Re-run:  python run_live.py clip rsbathla\n\n" % (live, e))
                    sys.exit(2)
                time.sleep(0.4)
    _bn = inject_boom(data, here)
    print("boom marks joined to %d players" % _bn)
    write_dashboard(data, out, src)


if __name__ == "__main__":
    main()
