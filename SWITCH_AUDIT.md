# Switch Audit — which signals we can ADD vs which are VIEW-only
*Every candidate "switch" in the model, run through one honest gate: does it predict realized booms BEYOND the base rate? If yes (residual-vs-base correlation is non-zero), it's eligible to move a boom probability (ADD). If not, the base already owns it — keep it for display only (VIEW). June 2026.*

**How to read.** `raw` = correlation of the signal with boom rate (inflated by volume/scoring overlap). `resid` = correlation with boom rate **after subtracting the modeled base** — this is the real test. `|resid|≥0.15` = **ADD**, `0.10–0.15` = **WEAK**, `<0.10` = **VIEW**. `LOW-N` = sample too small to trust (don't act). This is the in-sample upper bound (2025→2025); ADD switches still need the stricter 2024→2025 out-of-sample confirm before they're sized.

## QB
QB ceiling = **clean pocket + efficiency + environment**. Protection, O-line, off_q, env, YPA and the fused ceiling/boom scores all add beyond the base. Volume-ish stats (pass-TD/g, rush/g, pace, coverage-matchup) are already baked into the base → view-only.

**ADD (9):** `fus.protection_pctl` (+0.272), `fus.ceiling_pctl` (+0.242), `usage.dk_pg` (+0.212), `team_env.off_q` (+0.21), `fus.boom_pctl` (+0.186), `fus.oline_pctl` (-0.167), `team_env.env_idx` (+0.166), `adv2.ypa` (+0.165), `fus.spike_pctl` (+0.152)

**WEAK (3):** `adv2.rushtd_g`, `adv2.rushyd_pg`, `fus.matchup_pctl`

**VIEW (3):** `team_env.pace_pctl`, `adv2.rush_pg`, `adv2.ptd_pg`

**LOW-N (untrusted, 1):** `cspec.ratio`

| signal | n | raw | resid | verdict |
|---|---|---|---|---|
| fus.protection_pctl | 30 | +0.435 | +0.272 | ADD |
| fus.ceiling_pctl | 30 | +0.475 | +0.242 | ADD |
| usage.dk_pg | 29 | +0.459 | +0.212 | ADD |
| team_env.off_q | 30 | +0.4 | +0.21 | ADD |
| fus.boom_pctl | 30 | +0.396 | +0.186 | ADD |
| fus.oline_pctl | 30 | +0.027 | -0.167 | ADD |
| team_env.env_idx | 30 | +0.424 | +0.166 | ADD |
| adv2.ypa | 30 | +0.457 | +0.165 | ADD |
| fus.spike_pctl | 30 | +0.036 | +0.152 | ADD |
| adv2.rushtd_g | 30 | +0.044 | -0.127 | WEAK |
| adv2.rushyd_pg | 30 | +0.138 | -0.111 | WEAK |
| fus.matchup_pctl | 30 | -0.279 | -0.107 | WEAK |
| team_env.pace_pctl | 30 | +0.306 | +0.068 | VIEW |
| adv2.rush_pg | 30 | +0.175 | -0.03 | VIEW |
| adv2.ptd_pg | 30 | +0.442 | +0.027 | VIEW |
| cspec.ratio | 21 | +0.305 | +0.011 | LOW-N |

## RB
The standout: RB booms come from **yards-after-contact + O-line + matchup**, NOT volume. Carry share, targets, DK/g, total-TD/g, ceiling_pctl all test VIEW (redundant with base). yaco_att, fus.matchup_pctl, fus.oline_pctl genuinely ADD. Build RB ceiling on trench + creation, not raw touches.

**ADD (3):** `chart2.yaco_att(25)` (+0.241), `fus.matchup_pctl` (+0.213), `fus.oline_pctl` (+0.194)

**WEAK (7):** `usage.carry_share`, `chart2.success(25)`, `team_env.env_idx`, `fus.explosive_pctl`, `fus.yac_pctl`, `fus.boom_pctl`, `usage.ypc`

**VIEW (13):** `opp.route_pct`, `adv2.td_pg`, `team_env.off_q`, `team_env.pace_pctl`, `fus.run_eff_pctl`, `chart2.i5_pct(25)`, `usage.dk_pg`, `usage.tgt_share`, `chart2.exp_run(25)`, `fus.spike_pctl`, `chart2.mtf_att(25)`, `fus.rush_eff_pctl`, `fus.ceiling_pctl`

| signal | n | raw | resid | verdict |
|---|---|---|---|---|
| chart2.yaco_att(25) | 30 | +0.337 | +0.241 | ADD |
| fus.matchup_pctl | 36 | +0.394 | +0.213 | ADD |
| fus.oline_pctl | 36 | +0.281 | +0.194 | ADD |
| usage.carry_share | 33 | +0.223 | -0.145 | WEAK |
| chart2.success(25) | 30 | +0.259 | +0.12 | WEAK |
| team_env.env_idx | 34 | +0.308 | +0.116 | WEAK |
| fus.explosive_pctl | 36 | +0.279 | -0.115 | WEAK |
| fus.yac_pctl | 36 | +0.075 | -0.115 | WEAK |
| fus.boom_pctl | 36 | +0.029 | -0.103 | WEAK |
| usage.ypc | 33 | +0.265 | -0.101 | WEAK |
| opp.route_pct | 36 | +0.367 | -0.082 | VIEW |
| adv2.td_pg | 36 | +0.555 | +0.067 | VIEW |
| team_env.off_q | 34 | +0.264 | +0.057 | VIEW |
| team_env.pace_pctl | 34 | +0.069 | +0.055 | VIEW |
| fus.run_eff_pctl | 36 | +0.075 | -0.05 | VIEW |
| chart2.i5_pct(25) | 30 | +0.211 | +0.047 | VIEW |
| usage.dk_pg | 33 | +0.518 | -0.044 | VIEW |
| usage.tgt_share | 33 | +0.48 | +0.039 | VIEW |
| chart2.exp_run(25) | 30 | +0.242 | +0.028 | VIEW |
| fus.spike_pctl | 36 | -0.48 | +0.019 | VIEW |
| chart2.mtf_att(25) | 30 | +0.295 | +0.017 | VIEW |
| fus.rush_eff_pctl | 36 | +0.163 | -0.006 | VIEW |
| fus.ceiling_pctl | 36 | +0.458 | -0.004 | VIEW |

## WR
Richest position. **Coverage-beating (cspec ratio +0.43), route efficiency (TPRR/YPRR), separation vs man, red-zone target share, matchup, after-catch** all ADD. Pure volume/role (target share, DK/g, ceiling_pctl, aDOT, air-yard share, snap/route participation) is VIEW — the base owns it.

**ADD (11):** `cspec.ratio` (+0.43), `chart2.tprr(25)` (+0.405), `chart2.yprr(25)` (+0.336), `sep.man_sep_pctl` (+0.316), `sep.sep_pctl` (+0.291), `rz.rz_tgt_share` (+0.277), `fus.matchup_pctl` (+0.257), `chart2.yaco(25)` (+0.215), `cspec.pctl` (+0.205), `team_env.pace_pctl` (+0.186), `adv2.td_pg` (+0.181)

**WEAK (4):** `chart2.mtf(25)`, `chart2.yac(25)`, `adv2.tgt_share`, `usage.dk_pg`

**VIEW (17):** `fus.yac_pctl`, `team_env.off_q`, `fus.route_eff_pctl`, `team_env.env_idx`, `fus.spike_pctl`, `opp.route_pct`, `adv2.ypt`, `adv2.ay_share`, `adv2.aDOT`, `rz.ez_tgt_share`, `fus.oline_pctl`, `fus.boom_pctl`, `rz.ez_td_pg`, `fus.coverage_proof_pctl`, `fus.ceiling_pctl`, `fus.explosive_pctl`, `fus.separation_pctl`

| signal | n | raw | resid | verdict |
|---|---|---|---|---|
| cspec.ratio | 43 | +0.527 | +0.43 | ADD |
| chart2.tprr(25) | 50 | +0.662 | +0.405 | ADD |
| chart2.yprr(25) | 50 | +0.639 | +0.336 | ADD |
| sep.man_sep_pctl | 56 | +0.457 | +0.316 | ADD |
| sep.sep_pctl | 56 | +0.456 | +0.291 | ADD |
| rz.rz_tgt_share | 56 | +0.277 | +0.277 | ADD |
| fus.matchup_pctl | 56 | +0.151 | +0.257 | ADD |
| chart2.yaco(25) | 50 | +0.253 | +0.215 | ADD |
| cspec.pctl | 43 | +0.376 | +0.205 | ADD |
| team_env.pace_pctl | 53 | +0.31 | +0.186 | ADD |
| adv2.td_pg | 56 | +0.453 | +0.181 | ADD |
| chart2.mtf(25) | 50 | +0.138 | +0.149 | WEAK |
| chart2.yac(25) | 50 | +0.181 | +0.128 | WEAK |
| adv2.tgt_share | 56 | +0.523 | +0.118 | WEAK |
| usage.dk_pg | 52 | +0.553 | +0.108 | WEAK |
| fus.yac_pctl | 56 | +0.24 | +0.098 | VIEW |
| team_env.off_q | 53 | +0.369 | +0.095 | VIEW |
| fus.route_eff_pctl | 56 | +0.407 | +0.091 | VIEW |
| team_env.env_idx | 53 | +0.362 | +0.082 | VIEW |
| fus.spike_pctl | 56 | -0.394 | -0.076 | VIEW |
| opp.route_pct | 56 | +0.216 | -0.072 | VIEW |
| adv2.ypt | 56 | +0.253 | -0.066 | VIEW |
| adv2.ay_share | 56 | +0.248 | +0.065 | VIEW |
| adv2.aDOT | 56 | -0.071 | -0.044 | VIEW |
| rz.ez_tgt_share | 56 | +0.055 | -0.037 | VIEW |
| fus.oline_pctl | 56 | -0.017 | +0.033 | VIEW |
| fus.boom_pctl | 56 | +0.165 | -0.032 | VIEW |
| rz.ez_td_pg | 56 | +0.227 | -0.024 | VIEW |
| fus.coverage_proof_pctl | 56 | -0.078 | +0.02 | VIEW |
| fus.ceiling_pctl | 56 | +0.363 | +0.015 | VIEW |
| fus.explosive_pctl | 56 | -0.002 | +0.01 | VIEW |
| fus.separation_pctl | 56 | -0.045 | +0.0 | VIEW |

## TE
**LOW-N (only ~16 TEs with full charted+game data).** Verdicts not trustworthy at this sample — several large |r| values are noise. Needs the 2024 game data folded in before any TE switch is acted on. Treat all as VIEW for now.

**ADD (0):** —

**WEAK (0):** —

**VIEW (0):** —

**LOW-N (untrusted, 31):** `team_env.pace_pctl`, `rz.ez_tgt_share`, `rz.ez_td_pg`, `fus.oline_pctl`, `cspec.ratio`, `fus.coverage_proof_pctl`, `chart2.yaco(25)`, `fus.yac_pctl`, `rz.rz_tgt_share`, `fus.boom_pctl`, `chart2.yprr(25)`, `chart2.yac(25)`, `team_env.env_idx`, `fus.route_eff_pctl`, `cspec.pctl`, `chart2.mtf(25)`, `adv2.ay_share`, `chart2.tprr(25)`, `fus.matchup_pctl`, `fus.ceiling_pctl`, `fus.spike_pctl`, `sep.sep_pctl`, `adv2.td_pg`, `fus.separation_pctl`, `opp.route_pct`, `team_env.off_q`, `sep.man_sep_pctl`, `adv2.aDOT`, `adv2.ypt`, `usage.dk_pg`, `adv2.tgt_share`

| signal | n | raw | resid | verdict |
|---|---|---|---|---|
| team_env.pace_pctl | 16 | +0.364 | +0.409 | LOW-N |
| rz.ez_tgt_share | 16 | -0.178 | -0.401 | LOW-N |
| rz.ez_td_pg | 16 | -0.086 | -0.389 | LOW-N |
| fus.oline_pctl | 16 | -0.399 | -0.378 | LOW-N |
| cspec.ratio | 15 | +0.237 | +0.368 | LOW-N |
| fus.coverage_proof_pctl | 16 | +0.415 | +0.322 | LOW-N |
| chart2.yaco(25) | 14 | -0.174 | -0.285 | LOW-N |
| fus.yac_pctl | 16 | -0.04 | -0.278 | LOW-N |
| rz.rz_tgt_share | 16 | -0.091 | -0.223 | LOW-N |
| fus.boom_pctl | 16 | -0.262 | -0.198 | LOW-N |
| chart2.yprr(25) | 14 | -0.191 | -0.189 | LOW-N |
| chart2.yac(25) | 14 | -0.275 | -0.183 | LOW-N |
| team_env.env_idx | 16 | -0.186 | -0.172 | LOW-N |
| fus.route_eff_pctl | 16 | -0.157 | -0.164 | LOW-N |
| cspec.pctl | 15 | +0.293 | +0.162 | LOW-N |
| chart2.mtf(25) | 14 | -0.111 | -0.153 | LOW-N |
| adv2.ay_share | 16 | +0.201 | -0.15 | LOW-N |
| chart2.tprr(25) | 14 | +0.083 | -0.138 | LOW-N |
| fus.matchup_pctl | 16 | -0.052 | -0.136 | LOW-N |
| fus.ceiling_pctl | 16 | +0.482 | +0.099 | LOW-N |
| fus.spike_pctl | 16 | -0.445 | -0.096 | LOW-N |
| sep.sep_pctl | 16 | -0.027 | -0.077 | LOW-N |
| adv2.td_pg | 16 | +0.288 | +0.058 | LOW-N |
| fus.separation_pctl | 16 | -0.312 | +0.05 | LOW-N |
| opp.route_pct | 16 | +0.418 | +0.037 | LOW-N |
| team_env.off_q | 16 | +0.087 | +0.033 | LOW-N |
| sep.man_sep_pctl | 16 | -0.01 | -0.03 | LOW-N |
| adv2.aDOT | 16 | -0.103 | -0.029 | LOW-N |
| adv2.ypt | 16 | -0.065 | -0.017 | LOW-N |
| usage.dk_pg | 16 | +0.458 | -0.011 | LOW-N |
| adv2.tgt_share | 16 | +0.499 | -0.006 | LOW-N |
