# Best Ball 2026 — Build Contracts (shared interface for parallel work)

Format: DraftKings Best Ball, 12-team pods, **top-2 of 12 advance on W1–14 cumulative points**, then
single-week playoff gates **W15 (top 50%) → W16 (top 50%) → W17 (top 10%)**. Objective = maximize
advancement (volume) for the regular season AND overlay ceiling for W15/16/17. me = "rsbathla".

Existing engine (pipeline/, DO NOT rewrite — wrap it):
- sim_prod.py        compositional Monte Carlo (schedule-aware, Clay means, correlations)
- survival_chain.py  chain(rosters: {team:[names]}, me) -> DataFrame[team,p_adv,surv_W15,surv_W16,win_W17,title_share,W17_anchor,anchor_pieces]
- win_delta.py       win_deltas(rosters, me, cands, ns) -> (base{title,adv,w17}, {cand:{dtitle,dadv,dw17}})
- data: clay_2026.csv, schedule_2026.csv, games_by_week.json, byes_2026.json, correlation_structure.json,
        layer2_player_params.csv, merged_rankings_upload.csv, dk_adp.csv

Player names: normalize via survival_chain._norm; only names present in layer2/clay sim are gradeable.

## Contract 1 — engine/bbengine.py  (Agent A)
Clean importable API (run-dir agnostic; resolve paths to pipeline/):
- load_board() -> list[dict]: every draftable player {name,pos,team,adp,rank,proj,ceiling_p95,bye,playoff_up}
    (playoff_up filled from engine/playoff_overlay.csv if present, else 0.0)
- grade(rosters:dict, me="rsbathla") -> dict: {p_adv,surv_W15,surv_W16,win_W17,title_share,anchor}
- pick_values(rosters, me, candidates:list[str], ns=1500) -> {name:{dadv,dtitle,dw17}}
- parse_board(text:str, seat) -> {pick:int, round:int, seat, my_roster:[names], counts:{QB,RB,WR,TE}, available:[names]}
    (reuse logic from ../draft_assistant.py / ../draft_pick.py; handle live names + ADP-resolved pos/team)
Deliverable: module + engine/test_bbengine.py (smoke) that PASSES. Verify chain numbers reproduce.

## Contract 2 — engine/playoff_overlay.csv + docs/STRATEGY_SPEC.md + engine/tree_schema.json  (Agent B)
- playoff_overlay.csv: name,team,pos,w15_up,w16_up,w17_up,playoff_up  (per-player W15-17 ceiling overlay:
    team playoff-week matchup quality x player ceiling; normalize playoff_up to ~0..1)
- STRATEGY_SPEC.md: the construction decision rules for THIS format — positional build curves (target
    QB~2-3/RB~6/WR~8-9/TE~2-3 over 18 rounds), stack/anchor (QB+pass-catcher, bring-back), bye spread,
    and how the W15-17 overlay tilts late-round picks toward playoff-week upside.
- tree_schema.json: the JSON schema below (Contract 3) with one worked example.

## Contract 3 — Decision-tree JSON  (produced by Agent C engine/decision_tree.py, consumed by Agent D UI)
{
  "state": {"pick":int,"round":int,"seat":int,"roster":[{name,pos,team}],"counts":{QB,RB,WR,TE},"anchor":str},
  "headline": {"take": name, "dTitle": float, "dAdv": float, "why": str},
  "tree": {
    "label": "Pick 43 (R4)",
    "branches": [
      {"cond":"if <PlayerA> (elite WR) still on board","take":name,"pos":..,"dTitle":..,"dAdv":..,"dW17":..,
       "reason":str,"then":{ <next-pick subtree, same shape, 1-2 ply> }},
      ... 2-4 branches ordered best->fallback, last = "best available / need POS"
    ]
  }
}

## Contract 4 — engine/decision_tree.py  (Agent C)
build_tree(board, rosters, me, seat, plies=2) -> the JSON above. Branch on top availability scenarios at
our pick; value each candidate via pick_values; pick max blended score = 0.6*dTitle + 0.4*dAdv with the
construction rules + playoff_up tilt from round ~10 on. Look ahead 1-2 picks. Completion: valid tree for a
sample mid-draft state; recommendations maximize blended Δ and respect build curves.

## Contract 5 — bestball/decision_dashboard.html  (Agent D)
Self-contained, plain HTML/JS (NO custom elements — must render in any preview), inline data. Renders the
decision tree (collapsible branches), the headline pick, roster state, and a paste-a-board live box.
Completion: jsdom render 0 errors; tree expands; live paste produces a tree.
