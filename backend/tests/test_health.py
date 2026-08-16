"""
Unit tests for production health endpoints (/health/live, /health/ready, /health).
"""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_liveness_endpoint():
    """
    Test GET /health/live returns HTTP 200 and healthy status.
    """
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

    # Also verify via API v1 prefix
    v1_response = client.get("/api/v1/health/live")
    assert v1_response.status_code == 200
    assert v1_response.json() == {"status": "healthy"}


@patch("app.services.health_service.HealthService.check_postgres", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_neo4j", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_gemini", return_value=True)
def test_readiness_endpoint_success(mock_gemini, mock_neo4j, mock_postgres):
    """
    Test GET /health/ready returns HTTP 200 when all dependencies are healthy.
    """
    mock_postgres.return_value = True
    mock_neo4j.return_value = True

    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["neo4j"] == "healthy"
    assert data["dependencies"]["gemini"] == "configured"


@patch("app.services.health_service.HealthService.check_postgres", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_neo4j", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_gemini", return_value=True)
def test_readiness_endpoint_failure(mock_gemini, mock_neo4j, mock_postgres):
    """
    Test GET /health/ready returns HTTP 503 when a required dependency fails.
    """
    mock_postgres.return_value = False
    mock_neo4j.return_value = True

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unready"
    assert data["dependencies"]["postgres"] == "unhealthy"
    assert data["dependencies"]["neo4j"] == "healthy"


@patch("app.services.health_service.HealthService.check_postgres", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_neo4j", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_gemini", return_value=True)
def test_health_summary_endpoint(mock_gemini, mock_neo4j, mock_postgres):
    """
    Test GET /health returns structured operational health document.
    """
    mock_postgres.return_value = True
    mock_neo4j.return_value = True

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["neo4j"] == "healthy"
    assert data["dependencies"]["gemini"] == "configured"
