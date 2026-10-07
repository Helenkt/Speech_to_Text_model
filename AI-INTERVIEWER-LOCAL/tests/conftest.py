from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.account_importer import seed_demo_accounts


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def test_settings(tmp_path: Path, project_root: Path) -> Settings:
    return Settings(
        root_dir=project_root,
        database_path=tmp_path / "test.db",
        static_dir=project_root / "app" / "static",
        demo_data_dir=project_root / "data",
        whisper_download_root=tmp_path / "models" / "whisper",
        auto_seed_demo=False,
        evaluator_mode="rule",
    )


@pytest.fixture
def client(test_settings: Settings):
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        seed_demo_accounts(test_settings.database_path, test_settings.demo_data_dir)
        yield test_client


@pytest.fixture
def login_teacher(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": "teacher", "password": "Teacher@123"},
    )
    assert response.status_code == 200
    return response.json()["user"]


@pytest.fixture
def login_candidate(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": "candidate01", "password": "Candidate@123"},
    )
    assert response.status_code == 200
    return response.json()["user"]
