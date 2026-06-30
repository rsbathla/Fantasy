# BestBall Analytics API

A lightweight, read-only FastAPI service over the football-analytics pipeline's JSON
outputs, plus **one** guarded background rebuild. The web process **never imports
pandas or `core.py`** — it only reads JSON. The rebuild shells the pipeline out to a
**separate** process (that is where pandas runs).

## Run

```bash
cd api
pip install -r requirements.txt
./run.sh                      # http://127.0.0.1:8000  (interactive docs at /docs)
```

`run.sh` sets `PYTHONPATH=.` and launches `uvicorn app.main:app --reload`.

Configuration is via env vars (prefix `BESTBALL_`) or a local `.env`:

| Setting | Default | Notes |
|---|---|---|
| `BESTBALL_DATA_DIR` | repo root | Where the pipeline JSON lives. |
| `BESTBALL_CORS_ORIGINS` | `["*"]` | **Lock down in prod** to your dashboard origin(s). |
| `BESTBALL_REBUILD_API_KEY` | _unset_ | If unset, the rebuild route returns **503 `rebuild_disabled`**. |
| `BESTBALL_PIPELINE_CMD` | `python3 refactor/pipeline.py` | Runs with `cwd=DATA_DIR`. |
| `BESTBALL_MAX_PAGE_SIZE` | `200` | Upper bound for `page_size`. |

## Route design

All routes are under `/api/v1` except `/health`.

| Method | Path | Purpose | Validated query / path params |
|---|---|---|---|
| GET | `/health` | Liveness probe | — |
| GET | `/api/v1/meta` | Dataset counts, last-build (file mtimes), feature column count | — |
| GET | `/api/v1/players` | Paginated player summaries (fusion ⋈ dfs by slug) | `pos`∈{ALL,QB,RB,WR,TE}=ALL, `q`?, `flag`?, `min_consensus`∈[0,100]?, `sort`∈{consensus,divergence,adp,name}=consensus, `order`∈{asc,desc}=desc, `page`≥1=1, `page_size`∈[1,MAX]=50 |
| GET | `/api/v1/players/{player_id}` | Full profile (fusion models + dfs sources + flags) or 404 | `player_id` (slug) |
| GET | `/api/v1/dfs` | Paginated DFS scenario reads | `pos`, `q`?, `sort`∈{ceiling_consensus,ceiling_divergence,p_w17,adp,name}=ceiling_consensus, `order`, `page`, `page_size` |
| GET | `/api/v1/fusion` | Paginated raw fusion votes | `pos`, `q`?, `flag`?, `min_consensus`?, `sort`∈{consensus,divergence,adp,name}, `order`, `page`, `page_size` |
| GET | `/api/v1/defense` | 32 team defense profiles | `sort`∈{pass_cov,pass_rush,run_def,team}=pass_cov, `order` |
| GET | `/api/v1/defense/{team}` | Team detail (top contributors + moves_2026) or 404 | `team` matches `^[A-Z]{2,3}$` |
| GET | `/api/v1/gameplan/tiers` | Draft tiers | — |
| GET | `/api/v1/gameplan/stacks` | Correlation stacks | — |
| GET | `/api/v1/gameplan/team-priority` | Team attack priority | — |
| GET | `/api/v1/personnel` | All-team personnel summary | — |
| GET | `/api/v1/personnel/{team}` | Team personnel detail or 404 | `team` matches `^[A-Z]{2,3}$` |
| POST | `/api/v1/admin/rebuild` | Start background rebuild (one at a time) | header `X-API-Key` |
| GET | `/api/v1/admin/jobs/{job_id}` | Rebuild job status or 404 | header `X-API-Key`, `job_id` |

Player ids are produced by a tiny local `slugify(name)` (lowercase, strip
generational suffixes Jr/Sr/II–V, drop punctuation, hyphenate) — e.g.
`Ja'Marr Chase → jamarr-chase`. fusion and dfs are joined on this slug.

## Validation

Every query/path parameter is validated by FastAPI `Query`/`Path` constraints and
`Literal` enums (see the table). `page_size` is bounded by `MAX_PAGE_SIZE` (settings),
`min_consensus` to `[0,100]`, team codes to `^[A-Z]{2,3}$`. Output shape is enforced
by Pydantic response models. Any invalid input yields **422** in the standard error
envelope (the `RequestValidationError` handler is overridden), with the field errors
in `error.details`.

## Error model

One envelope for **every** error response:

```json
{
  "error": { "code": "<machine_code>", "message": "<human>", "details": [] },
  "request_id": "<uuid>"
}
```

| Situation | Status | `error.code` |
|---|---|---|
| Invalid params | 422 | `validation_error` (details = field errors) |
| Missing player / team / job | 404 | `player_not_found` / `team_not_found` / `job_not_found` |
| Rebuild already running | 409 | `rebuild_in_progress` |
| Missing/bad `X-API-Key` | 401 | `invalid_api_key` |
| Rebuild not configured | 503 | `rebuild_disabled` |
| Unhandled exception | 500 | `internal_error` (full trace logged; generic message returned — never leaks internals) |

Every response carries an `X-Request-ID` (assigned or propagated from the request)
and an `X-Response-Time-ms` header, set by middleware.

## Rebuild job design

- The runner is an **injectable callable** (`RunnerFn`). Default `subprocess_runner`
  shells `PIPELINE_CMD` with `cwd=DATA_DIR` and captures combined stdout/stderr.
  Tests inject a fake runner so the real pipeline never runs.
- Jobs live in a **thread-safe in-memory registry**: `{job_id, status, started_at,
  finished_at, returncode, log_tail}` with status `queued → running → succeeded|failed`.
- **One at a time**: a second rebuild while one is active returns **409**.
- The route requires a valid `X-API-Key` (constant-time compare); if no key is
  configured the route returns **503** instead of running unguarded.

## Architecture (layers)

```
api/app/
  main.py          app factory: CORS, request-id+timing middleware, exception handlers, routers, OpenAPI tags
  config.py        pydantic-settings Settings
  deps.py          Depends: get_store, pagination_params, team_code, require_api_key
  errors.py        AppError/NotFound/Conflict/... + the envelope handlers
  util.py          slugify (no pandas, no core.py)
  schemas/         Pydantic request (query) + response models
  repositories/    DataStore: load+cache JSON, mtime invalidation, thread-safe
  services/        players/defense/gameplan/personnel/meta/rebuild logic (no HTTP here)
  routers/         thin HTTP handlers -> services
tests/test_api.py  pytest + TestClient (rebuild runner mocked)
```

Routers contain no business logic; services contain no HTTP; only `DataStore`
touches the JSON files.

## curl examples

```bash
curl -s localhost:8000/health
curl -s "localhost:8000/api/v1/players?pos=WR&sort=consensus&order=desc&page=1&page_size=5"
curl -s "localhost:8000/api/v1/players?flag=CONSENSUS%20STUD&min_consensus=70"
curl -s localhost:8000/api/v1/players/jamarr-chase
curl -s "localhost:8000/api/v1/dfs?sort=p_w17&order=desc&page_size=10"
curl -s "localhost:8000/api/v1/defense?sort=pass_rush&order=desc"
curl -s localhost:8000/api/v1/defense/KC
curl -s localhost:8000/api/v1/gameplan/tiers
curl -s localhost:8000/api/v1/personnel/DET

# guarded rebuild (requires BESTBALL_REBUILD_API_KEY set)
curl -s -X POST localhost:8000/api/v1/admin/rebuild -H "X-API-Key: $BESTBALL_REBUILD_API_KEY"
curl -s localhost:8000/api/v1/admin/jobs/<job_id> -H "X-API-Key: $BESTBALL_REBUILD_API_KEY"

# validation error (422)
curl -s "localhost:8000/api/v1/players?pos=ZZ"
```
