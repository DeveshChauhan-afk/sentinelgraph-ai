"""
Unit tests for GraphQueryService fast-triage risk scoring logic.

Covers:
1. 0 incidents (isolated / negative controls)
2. 1 incident (initial intake baseline)
3. 2 incidents (initial correlation threshold)
4. 5 incidents (emerging cluster sizing)
5. 10 incidents (established syndicate sizing)
6. Large networks (progressively higher scores for large clusters)
7. LOW / MEDIUM / HIGH boundary cutoffs (40 = MEDIUM, 70 = HIGH)
8. Maximum score ceiling invariant (score never exceeds 100)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from dotenv import load_dotenv
import pytest

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from app.graph.query_service import GraphQueryService  # noqa: E402


@pytest.fixture
def query_service() -> GraphQueryService:
    """Provide GraphQueryService with a mocked repository."""
    mock_repo = MagicMock()
    return GraphQueryService(repository=mock_repo)


def test_calculate_risk_zero_incidents(query_service: GraphQueryService) -> None:
    """Test 0 incidents results in LOW risk and 0 base score."""
    # Zero incidents, zero neighbors
    score, level = query_service._calculate_risk(incident_count=0, neighbor_count=0)
    assert score == 0
    assert level == "LOW"

    # Zero incidents with high neighbor count (e.g. orphan entity with neighbors)
    score_with_neighbors, level_with_neighbors = query_service._calculate_risk(
        incident_count=0, neighbor_count=5
    )
    assert score_with_neighbors == 20
    assert level_with_neighbors == "LOW"


def test_calculate_risk_one_incident(query_service: GraphQueryService) -> None:
    """Test 1 incident yields base score of 25 (LOW) and 45 (MEDIUM) with >3 neighbors."""
    # 1 incident, <= 3 neighbors
    score, level = query_service._calculate_risk(incident_count=1, neighbor_count=2)
    assert score == 25
    assert level == "LOW"

    # 1 incident, rich connectivity (>3 neighbors)
    score_rich, level_rich = query_service._calculate_risk(
        incident_count=1, neighbor_count=4
    )
    assert score_rich == 45
    assert level_rich == "MEDIUM"


def test_calculate_risk_two_incidents(query_service: GraphQueryService) -> None:
    """Test 2 incidents hits the exact 40 MEDIUM boundary without multi-neighbor bonus."""
    # 2 incidents, <= 3 neighbors -> 25 + 15 = 40 (exact MEDIUM boundary)
    score, level = query_service._calculate_risk(incident_count=2, neighbor_count=1)
    assert score == 40
    assert level == "MEDIUM"

    # 2 incidents with >3 neighbors -> 40 + 20 = 60 (MEDIUM)
    score_rich, level_rich = query_service._calculate_risk(
        incident_count=2, neighbor_count=4
    )
    assert score_rich == 60
    assert level_rich == "MEDIUM"


def test_calculate_risk_five_incidents(query_service: GraphQueryService) -> None:
    """Test 5 incidents (emerging cluster) yields 55 (MEDIUM) and 75 (HIGH) with neighbors."""
    # 5 incidents, <= 3 neighbors -> 40 + 3*5 = 55
    score, level = query_service._calculate_risk(incident_count=5, neighbor_count=2)
    assert score == 55
    assert level == "MEDIUM"

    # 5 incidents with >3 neighbors -> 55 + 20 = 75
    score_rich, level_rich = query_service._calculate_risk(
        incident_count=5, neighbor_count=4
    )
    assert score_rich == 75
    assert level_rich == "HIGH"


def test_calculate_risk_ten_incidents(query_service: GraphQueryService) -> None:
    """Test 10 incidents hits the 70 HIGH boundary even without rich connectivity."""
    # 10 incidents, <= 3 neighbors -> 55 + 5*3 = 70 (exact HIGH threshold)
    score, level = query_service._calculate_risk(incident_count=10, neighbor_count=1)
    assert score == 70
    assert level == "HIGH"

    # 10 incidents with >3 neighbors -> 70 + 20 = 90
    score_rich, level_rich = query_service._calculate_risk(
        incident_count=10, neighbor_count=5
    )
    assert score_rich == 90
    assert level_rich == "HIGH"


def test_calculate_risk_large_network(query_service: GraphQueryService) -> None:
    """Test large networks receive progressively higher scores without artificial plateaus."""
    # 20 incidents
    score_20, level_20 = query_service._calculate_risk(
        incident_count=20, neighbor_count=2
    )
    assert score_20 == 80  # 70 + 10*1
    assert level_20 == "HIGH"

    # 30 incidents
    score_30, level_30 = query_service._calculate_risk(
        incident_count=30, neighbor_count=2
    )
    assert score_30 == 90  # 70 + 20*1
    assert level_30 == "HIGH"

    # 35 incidents with >3 neighbors
    score_35, level_35 = query_service._calculate_risk(
        incident_count=35, neighbor_count=5
    )
    assert score_35 == 100  # min(70 + 25*1 + 20, 100) = 100
    assert level_35 == "HIGH"

    # 50 incidents (large syndicate bridge)
    score_50, level_50 = query_service._calculate_risk(
        incident_count=50, neighbor_count=3
    )
    assert score_50 == 100  # min(70 + 40*1, 100) = 100
    assert level_50 == "HIGH"

    # Verify monotonic progression: score strictly increases with network size
    scores = [
        query_service._calculate_risk(i, 2)[0]
        for i in [0, 1, 2, 3, 4, 5, 8, 10, 15, 20, 25, 30]
    ]
    for i in range(len(scores) - 1):
        assert scores[i] < scores[i + 1], f"Expected score strictly increasing at index {i}"


def test_calculate_risk_boundary_thresholds(query_service: GraphQueryService) -> None:
    """Test exact LOW, MEDIUM, and HIGH classification boundaries."""
    # Score 0 -> LOW
    assert query_service._calculate_risk(0, 0) == (0, "LOW")

    # Score 20 -> LOW (0 incidents, 4 neighbors)
    assert query_service._calculate_risk(0, 4) == (20, "LOW")

    # Score 25 -> LOW (1 incident, 0 neighbors)
    assert query_service._calculate_risk(1, 0) == (25, "LOW")

    # Score 40 -> MEDIUM (exact threshold)
    assert query_service._calculate_risk(2, 0) == (40, "MEDIUM")

    # Score 45 -> MEDIUM (1 incident, 4 neighbors)
    assert query_service._calculate_risk(1, 4) == (45, "MEDIUM")

    # Score 55 -> MEDIUM (5 incidents, 0 neighbors)
    assert query_service._calculate_risk(5, 0) == (55, "MEDIUM")

    # Score 60 -> MEDIUM (2 incidents, 4 neighbors)
    assert query_service._calculate_risk(2, 4) == (60, "MEDIUM")

    # Score 70 -> HIGH (exact threshold: 10 incidents, 0 neighbors)
    assert query_service._calculate_risk(10, 0) == (70, "HIGH")

    # Score 75 -> HIGH (5 incidents, 4 neighbors)
    assert query_service._calculate_risk(5, 4) == (75, "HIGH")

    # Score 90 -> HIGH (10 incidents, 4 neighbors)
    assert query_service._calculate_risk(10, 4) == (90, "HIGH")


def test_calculate_risk_never_exceeds_100(query_service: GraphQueryService) -> None:
    """Test score ceiling invariant: score never exceeds 100 under extreme network size."""
    extreme_cases = [
        (40, 10),
        (50, 20),
        (100, 50),
        (500, 100),
        (10000, 5000),
    ]
    for inc_cnt, neigh_cnt in extreme_cases:
        score, level = query_service._calculate_risk(
            incident_count=inc_cnt, neighbor_count=neigh_cnt
        )
        assert score == 100, f"Failed for {inc_cnt} incidents: score was {score}"
        assert level == "HIGH"
