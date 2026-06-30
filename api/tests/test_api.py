"""End-to-end API tests (FastAPI TestClient). The rebuild runner is MOCKED via the
`client` fixture's FakeRunner, so the real pandas pipeline never runs here.
"""
import time

# A WR present in BOTH fusion and dfs -> exercises the join path.
JOIN_SLUG = "puka-nacua"
A_FLAG = "BOOM MERCHANT"
A_TEAM = "ARI"


# ---- envelope helper ---------------------------------------------------------

def assert_error_envelope(body, expected_code=None):
    assert set(body.keys()) == {"error", "request_id"}, body
    err = body["error"]
    assert set(err.keys()) == {"code", "message", "details"}, err
    assert isinstance(err["code"], str) and err["code"]
    assert isinstance(err["message"], str) and err["message"]
    assert isinstance(err["details"], list)
    assert body["request_id"]  # populated by middleware
    if expected_code:
        assert err["code"] == expected_code, err


# ---- 1. health ---------------------------------------------------------------

def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---- 2. players: paginated shape + filters + sort ----------------------------

def test_players_paginated_shape(client):
    r = client.get("/api/v1/players", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"data", "pagination"}
    pg = body["pagination"]
    assert set(pg.keys()) == {"page", "page_size", "total", "total_pages"}
    assert pg["page"] == 1 and pg["page_size"] == 5
    assert pg["total"] > 0
    assert len(body["data"]) <= 5
    row = body["data"][0]
    # joined summary fields present
    for k in ("id", "name", "pos", "consensus", "flags"):
        assert k in row


def test_players_pos_filter(client):
    r = client.get("/api/v1/players", params={"pos": "WR", "page_size": 50})
    assert r.status_code == 200
    rows = r.json()["data"]
    assert rows, "expected some WRs"
    assert all(row["pos"] == "WR" for row in rows)


def test_players_q_search(client):
    r = client.get("/api/v1/players", params={"q": "chase"})
    assert r.status_code == 200
    rows = r.json()["data"]
    assert rows, "expected a match for 'chase'"
    assert all("chase" in row["name"].lower() for row in rows)


def test_players_sort_order(client):
    r = client.get("/api/v1/players", params={"sort": "consensus", "order": "desc", "page_size": 20})
    vals = [row["consensus"] for row in r.json()["data"] if row["consensus"] is not None]
    assert vals == sorted(vals, reverse=True)

    r2 = client.get("/api/v1/players", params={"sort": "adp", "order": "asc", "page_size": 20})
    adps = [row["adp"] for row in r2.json()["data"] if row["adp"] is not None]
    assert adps == sorted(adps)


def test_players_flag_filter(client):
    r = client.get("/api/v1/players", params={"flag": A_FLAG, "page_size": 100})
    assert r.status_code == 200
    rows = r.json()["data"]
    assert rows, f"expected players with flag {A_FLAG}"
    assert all(A_FLAG in row["flags"] for row in rows)


# ---- 3. invalid params -> 422 envelope --------------------------------------

def test_bad_pos_422(client):
    r = client.get("/api/v1/players", params={"pos": "ZZ"})
    assert r.status_code == 422
    assert_error_envelope(r.json(), "validation_error")
    assert r.json()["error"]["details"], "expected field-level details"


def test_page_zero_422(client):
    r = client.get("/api/v1/players", params={"page": 0})
    assert r.status_code == 422
    assert_error_envelope(r.json(), "validation_error")


def test_sort_bogus_422(client):
    r = client.get("/api/v1/players", params={"sort": "bogus"})
    assert r.status_code == 422
    assert_error_envelope(r.json(), "validation_error")


def test_page_size_over_max_422(client):
    r = client.get("/api/v1/players", params={"page_size": 9999})
    assert r.status_code == 422
    assert_error_envelope(r.json(), "validation_error")


# ---- 4./5. not found envelopes ----------------------------------------------

def test_player_not_found_404(client):
    r = client.get("/api/v1/players/this-player-does-not-exist")
    assert r.status_code == 404
    assert_error_envelope(r.json(), "player_not_found")


def test_defense_bad_team_pattern_422(client):
    # lowercase / wrong pattern -> path validation 422
    r = client.get("/api/v1/defense/zz")
    assert r.status_code == 422
    assert_error_envelope(r.json(), "validation_error")


def test_defense_unknown_team_404(client):
    # valid pattern, but no such team -> 404
    r = client.get("/api/v1/defense/ZZZ")
    assert r.status_code == 404
    assert_error_envelope(r.json(), "team_not_found")


# ---- 6. real player slug resolves with joined fusion + dfs -------------------

def test_real_player_profile_join(client):
    r = client.get(f"/api/v1/players/{JOIN_SLUG}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == JOIN_SLUG
    assert body["name"]
    assert isinstance(body["models"], dict) and body["models"], "fusion models present"
    assert isinstance(body["flags"], list)
    assert body["dfs"] is not None, "dfs side joined"
    assert "sources" in body["dfs"]


# ---- 7. guarded rebuild + job lifecycle -------------------------------------

def test_rebuild_requires_key_401(client):
    r = client.post("/api/v1/admin/rebuild")  # no X-API-Key
    assert r.status_code == 401
    assert_error_envelope(r.json(), "invalid_api_key")


def test_rebuild_disabled_when_no_key_503(client_no_key):
    r = client_no_key.post("/api/v1/admin/rebuild", headers={"X-API-Key": "anything"})
    assert r.status_code == 503
    assert_error_envelope(r.json(), "rebuild_disabled")


def test_rebuild_accepts_then_conflicts_then_status(client):
    runner = client.app.state._fake_runner
    runner.block = True  # keep first job 'running'
    headers = {"X-API-Key": "test-secret-key"}

    r1 = client.post("/api/v1/admin/rebuild", headers=headers)
    assert r1.status_code == 202
    body1 = r1.json()
    assert body1["status"] == "queued"
    job_id = body1["job_id"]
    assert job_id

    # wait until the runner thread has actually entered (job -> running)
    assert runner.started.wait(timeout=5)

    # second concurrent rebuild -> 409 conflict
    r2 = client.post("/api/v1/admin/rebuild", headers=headers)
    assert r2.status_code == 409
    assert_error_envelope(r2.json(), "rebuild_in_progress")

    # job status reachable (200) while running
    rs = client.get(f"/api/v1/admin/jobs/{job_id}", headers=headers)
    assert rs.status_code == 200
    js = rs.json()
    assert js["job_id"] == job_id
    assert js["status"] in ("queued", "running")

    # release the runner; job should finish succeeded
    runner.release()
    deadline = time.time() + 5
    final = None
    while time.time() < deadline:
        final = client.get(f"/api/v1/admin/jobs/{job_id}", headers=headers).json()
        if final["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.02)
    assert final["status"] == "succeeded", final
    assert final["returncode"] == 0
    assert final["log_tail"], "expected captured log tail"
    # the runner was invoked with the configured pipeline command
    assert runner.calls and runner.calls[0][0][:2] == ["python3", "refactor/pipeline.py"]


def test_job_not_found_404(client):
    r = client.get("/api/v1/admin/jobs/nope", headers={"X-API-Key": "test-secret-key"})
    assert r.status_code == 404
    assert_error_envelope(r.json(), "job_not_found")


def test_jobs_require_key_401(client):
    r = client.get("/api/v1/admin/jobs/whatever")  # no key
    assert r.status_code == 401
    assert_error_envelope(r.json(), "invalid_api_key")


# ---- 8. every response carries X-Request-ID ----------------------------------

def test_request_id_header_present(client):
    for path in ("/health", "/api/v1/meta", "/api/v1/players?page_size=1", "/api/v1/defense"):
        r = client.get(path)
        assert r.headers.get("X-Request-ID"), path
        assert r.headers.get("X-Response-Time-ms"), path


def test_request_id_propagated(client):
    r = client.get("/health", headers={"X-Request-ID": "my-trace-123"})
    assert r.headers.get("X-Request-ID") == "my-trace-123"


# ---- extra coverage: meta / dfs / fusion / defense list / gameplan / personnel

def test_meta_shape(client):
    r = client.get("/api/v1/meta")
    assert r.status_code == 200
    body = r.json()
    assert "datasets" in body and "fusion" in body["datasets"]
    assert body["datasets"]["fusion"]["count"] > 0
    assert body["feature_columns"] and body["feature_columns"] > 0
    assert body["last_build"]


def test_dfs_list_sort(client):
    r = client.get("/api/v1/dfs", params={"sort": "ceiling_consensus", "order": "desc", "page_size": 10})
    assert r.status_code == 200
    vals = [row["ceiling_consensus"] for row in r.json()["data"] if row["ceiling_consensus"] is not None]
    assert vals == sorted(vals, reverse=True)


def test_fusion_list(client):
    r = client.get("/api/v1/fusion", params={"pos": "QB", "page_size": 5})
    assert r.status_code == 200
    rows = r.json()["data"]
    assert all(row["pos"] == "QB" for row in rows)
    assert all("models" in row for row in rows)


def test_defense_list_and_detail(client):
    r = client.get("/api/v1/defense", params={"sort": "pass_cov", "order": "desc"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 32
    r2 = client.get(f"/api/v1/defense/{A_TEAM}")
    assert r2.status_code == 200
    d = r2.json()
    assert d["team"] == A_TEAM
    assert isinstance(d["top_coverage"], list)
    assert isinstance(d["moves_2026"], list)


def test_gameplan_endpoints(client):
    for path in ("/api/v1/gameplan/tiers", "/api/v1/gameplan/stacks", "/api/v1/gameplan/team-priority"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "data" in r.json() and "count" in r.json()


def test_personnel_endpoints(client):
    r = client.get("/api/v1/personnel")
    assert r.status_code == 200
    assert r.json()["count"] == 32
    r2 = client.get(f"/api/v1/personnel/{A_TEAM}")
    assert r2.status_code == 200
    assert r2.json()["team"] == A_TEAM
