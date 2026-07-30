"""
Unit tests for Golden Investigation Dataset (Sprint 9.5 Phase 9.5.1).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.evaluation.golden_dataset import GoldenScenario, get_golden_scenarios
from app.schemas.investigation_summary import InvestigationSummary


def test_golden_scenarios_loading():
    """
    Test loading all fixed golden investigation scenarios.
    """
    scenarios = get_golden_scenarios()

    assert "SIMPLE_FRAUD_CASE" in scenarios
    assert "ENTITY_REUSE_CASE" in scenarios
    assert "LARGE_FRAUD_RING" in scenarios

    for scenario_id, scenario in scenarios.items():
        assert isinstance(scenario, GoldenScenario)
        assert scenario.scenario_id == scenario_id
        assert isinstance(scenario.summary, InvestigationSummary)
        assert scenario.expected_risk_level in ("HIGH", "CRITICAL", "MEDIUM", "LOW")
        assert len(scenario.expected_citation_ids) > 0


def test_golden_simple_fraud_case():
    """
    Test specific properties of SIMPLE_FRAUD_CASE scenario.
    """
    scenarios = get_golden_scenarios()
    case = scenarios["SIMPLE_FRAUD_CASE"]

    assert case.summary.overview.target_value == "+919876543210"
    assert case.expected_risk_level == "HIGH"
    assert case.expected_finding_count == 1


def test_golden_entity_reuse_case():
    """
    Test specific properties of ENTITY_REUSE_CASE scenario.
    """
    scenarios = get_golden_scenarios()
    case = scenarios["ENTITY_REUSE_CASE"]

    assert case.summary.overview.target_value == "scammer@upi"
    assert case.expected_risk_level == "CRITICAL"


def test_golden_large_fraud_ring():
    """
    Test specific properties of LARGE_FRAUD_RING scenario.
    """
    scenarios = get_golden_scenarios()
    case = scenarios["LARGE_FRAUD_RING"]

    assert case.summary.overview.target_value == "RING-999"
    assert case.summary.overview.total_complaints == 12


def test_golden_scenario_immutability():
    """
    Test that GoldenScenario models are immutable.
    """
    scenarios = get_golden_scenarios()
    simple = scenarios["SIMPLE_FRAUD_CASE"]

    with pytest.raises((ValidationError, TypeError, AttributeError)):
        simple.name = "Modified Name"
