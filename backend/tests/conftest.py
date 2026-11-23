import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

# Configure the app before it is imported: throwaway SQLite DB, known secret, no API key.
_DB_DIR = tempfile.mkdtemp(prefix="dashcam-test-")
# TEST_DATABASE_URL lets CI run the same suite against PostgreSQL (the Supabase schema).
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{Path(_DB_DIR) / 'test.db'}"
)
os.environ["SIGNING_SECRET"] = "test-secret"
os.environ.pop("API_KEY", None)

from make_sample_videos import make_all  # noqa: E402


@pytest.fixture(scope="session")
def videos(tmp_path_factory) -> dict[str, Path]:
    return make_all(tmp_path_factory.mktemp("videos"), seconds=8.0)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
