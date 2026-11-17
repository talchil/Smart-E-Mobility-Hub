import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.seed_data import load_seed


@pytest.fixture(autouse=True)
def reset_store():
    """Clear the store before and after every test."""
    store.reset()
    yield
    store.reset()


@pytest.fixture
def seeded_store():
    """Populate the store with hard-coded seed data."""
    load_seed()
    return store


@pytest.fixture
def client():
    """FastAPI TestClient bound to the app."""
    return TestClient(app)