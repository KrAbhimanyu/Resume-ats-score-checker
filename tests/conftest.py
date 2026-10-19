import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI test client fixture."""
    return TestClient(app)


@pytest.fixture(scope="session")
def fixtures_dir() -> str:
    """Path to fixtures directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


@pytest.fixture(scope="session")
def sample_senior_pdf(fixtures_dir) -> bytes:
    with open(os.path.join(fixtures_dir, "sample_resumes", "senior_software_engineer.pdf"), "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def sample_senior_docx(fixtures_dir) -> bytes:
    with open(os.path.join(fixtures_dir, "sample_resumes", "senior_software_engineer.docx"), "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def sample_analyst_pdf(fixtures_dir) -> bytes:
    with open(os.path.join(fixtures_dir, "sample_resumes", "entry_level_analyst.pdf"), "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def sample_fullstack_job(fixtures_dir) -> str:
    with open(os.path.join(fixtures_dir, "sample_jobs", "fullstack_engineer.txt"), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="session")
def sample_analyst_job(fixtures_dir) -> str:
    with open(os.path.join(fixtures_dir, "sample_jobs", "data_analyst.txt"), "r", encoding="utf-8") as f:
        return f.read()
