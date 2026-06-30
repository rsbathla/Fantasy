"""Test fixtures.

- Puts `api/` on sys.path so `from app.main import create_app` resolves.
- Builds the app with a MOCKED rebuild runner so the REAL pipeline (pandas) never
  runs during tests. The mock blocks until released, letting us assert the
  one-at-a-time 409 behavior deterministically.
"""
import os
import sys
import threading

import pytest

_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.rebuild_service import RunnerResult  # noqa: E402

_REPO_ROOT = os.path.dirname(_API_DIR)


class FakeRunner:
    """A controllable stand-in for subprocess_runner.

    By default it blocks on an Event so the job stays 'running' until released;
    this lets a test fire a second rebuild and observe the 409.
    """

    def __init__(self):
        self.gate = threading.Event()
        self.started = threading.Event()
        self.calls = []
        self.block = True
        self.returncode = 0

    def __call__(self, cmd, cwd):
        self.calls.append((list(cmd), cwd))
        self.started.set()
        if self.block:
            self.gate.wait(timeout=5)
        return RunnerResult(returncode=self.returncode, log_lines=["mock build line 1", "mock build done"])

    def release(self):
        self.gate.set()


@pytest.fixture
def fake_runner():
    return FakeRunner()


@pytest.fixture
def settings_with_key():
    return Settings(DATA_DIR=_REPO_ROOT, REBUILD_API_KEY="test-secret-key", CORS_ORIGINS=["*"])


@pytest.fixture
def settings_no_key():
    return Settings(DATA_DIR=_REPO_ROOT, REBUILD_API_KEY=None, CORS_ORIGINS=["*"])


@pytest.fixture
def client(settings_with_key, fake_runner):
    from fastapi.testclient import TestClient
    app = create_app(settings=settings_with_key, rebuild_runner=fake_runner)
    app.state._fake_runner = fake_runner  # expose for tests
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_no_key(settings_no_key, fake_runner):
    from fastapi.testclient import TestClient
    app = create_app(settings=settings_no_key, rebuild_runner=fake_runner)
    with TestClient(app) as c:
        yield c
