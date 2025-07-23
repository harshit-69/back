import sys
import os
import pytest
from httpx import AsyncClient

# Get the backend directory path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the backend directory to Python path
sys.path.insert(0, backend_dir)

# Now import your FastAPI app
from app.main import app

@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client