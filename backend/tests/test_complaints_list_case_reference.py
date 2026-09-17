"""
Unit and integration tests for IncidentListResponse case_reference serialization.

Verifies that:
1. IncidentListResponse schema includes case_reference with optional string semantics.
2. GET /api/v1/complaints/ serializes case_reference for both populated and null values.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_incident_service
from app.main import app
from app.models.enums import IncidentSource, IncidentStatus, Priority, ReporterType
from app.models.incident import Incident
from app.schemas.incident import IncidentListResponse
from app.services.incident_service import IncidentService


def test_incident_list_response_schema_fields() -> None:
    """Ensure IncidentListResponse defines case_reference with Optional[str] semantics."""
    assert "case_reference" in IncidentListResponse.model_fields
    field_info = IncidentListResponse.model_fields["case_reference"]
    assert field_info.default is None


def test_incident_list_response_from_attributes_validation() -> None:
    """Ensure IncidentListResponse correctly reads case_reference from an ORM-like entity."""
    mock_incident = MagicMock(spec=Incident)
    mock_incident.id = uuid4()
    mock_incident.title = "Suspicious KYC Transfer"
    mock_incident.status = IncidentStatus.UNDER_INVESTIGATION
    mock_incident.priority = Priority.HIGH
    mock_incident.created_at = datetime.now(timezone.utc)
    mock_incident.reporter_type = ReporterType.CITIZEN
    mock_incident.source = IncidentSource.WEB_PORTAL
    mock_incident.risk_score = 0.85
    mock_incident.graph_node_id = None
    mock_incident.case_reference = "DEMO-KYCSUSPICIOUS-AB12CD34"

    dto = IncidentListResponse.model_validate(mock_incident)
    assert dto.case_reference == "DEMO-KYCSUSPICIOUS-AB12CD34"
    assert dto.risk_score == 0.85
    assert dto.title == "Suspicious KYC Transfer"


def test_incident_list_response_none_case_reference() -> None:
    """Ensure IncidentListResponse handles None case_reference without error."""
    mock_incident = MagicMock(spec=Incident)
    mock_incident.id = uuid4()
    mock_incident.title = "Unreferenced Incident"
    mock_incident.status = IncidentStatus.NEW
    mock_incident.priority = Priority.LOW
    mock_incident.created_at = datetime.now(timezone.utc)
    mock_incident.reporter_type = ReporterType.BANK
    mock_incident.source = IncidentSource.API
    mock_incident.risk_score = None
    mock_incident.graph_node_id = None
    mock_incident.case_reference = None

    dto = IncidentListResponse.model_validate(mock_incident)
    assert dto.case_reference is None


def test_list_complaints_endpoint_serializes_case_reference() -> None:
    """Ensure GET /api/v1/complaints/ endpoint serializes case_reference in JSON response."""
    inc_1 = MagicMock(spec=Incident)
    inc_1.id = uuid4()
    inc_1.title = "Alpha KYC Mule Transfer"
    inc_1.status = IncidentStatus.UNDER_INVESTIGATION
    inc_1.priority = Priority.HIGH
    inc_1.created_at = datetime.now(timezone.utc)
    inc_1.reporter_type = ReporterType.BANK
    inc_1.source = IncidentSource.API
    inc_1.risk_score = 0.90
    inc_1.graph_node_id = None
    inc_1.case_reference = "DEMO-ALPHAKYCMULE-A1B2C3D4"

    inc_2 = MagicMock(spec=Incident)
    inc_2.id = uuid4()
    inc_2.title = "Independent Control Case"
    inc_2.status = IncidentStatus.NEW
    inc_2.priority = Priority.LOW
    inc_2.created_at = datetime.now(timezone.utc)
    inc_2.reporter_type = ReporterType.CITIZEN
    inc_2.source = IncidentSource.WEB_PORTAL
    inc_2.risk_score = 0.0
    inc_2.graph_node_id = None
    inc_2.case_reference = None

    mock_service = MagicMock(spec=IncidentService)
    mock_service.list_incidents = AsyncMock(return_value=[inc_1, inc_2])

    app.dependency_overrides[get_incident_service] = lambda: mock_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/complaints/?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify item 1
        assert data[0]["id"] == str(inc_1.id)
        assert data[0]["title"] == "Alpha KYC Mule Transfer"
        assert data[0]["case_reference"] == "DEMO-ALPHAKYCMULE-A1B2C3D4"
        assert data[0]["risk_score"] == 0.90
        assert data[0]["graph_node_id"] == f"complaint:{inc_1.id}"

        # Verify item 2 (with null case_reference)
        assert data[1]["id"] == str(inc_2.id)
        assert data[1]["title"] == "Independent Control Case"
        assert data[1]["case_reference"] is None
        assert data[1]["risk_score"] == 0.0
        assert data[1]["graph_node_id"] == f"complaint:{inc_2.id}"

    finally:
        app.dependency_overrides.clear()
