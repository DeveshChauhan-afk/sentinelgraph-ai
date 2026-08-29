"""
Regression tests for Sprint 12.8B: Grafana Operations Dashboard:
1. Dashboard file exists and is valid JSON.
2. Required 8 telemetry panels exist with titles, units, descriptions, and grid layout.
3. PromQL queries reference only verified existing metrics from app/core/metrics.py.
4. No hardcoded localhost or machine-specific datasource URLs exist.
5. Datasource is parameterized via template variables (${DS_PROMETHEUS}).
6. No raw PII or unbounded dynamic identifiers are present in panel queries or metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

from app.core import metrics as core_metrics_module


# ============================================================================
# 1. Dashboard File Loading & JSON Validity
# ============================================================================


def get_dashboard_file_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "monitoring" / "grafana" / "dashboards" / "sentinelgraph-operations.json"


def load_dashboard_json() -> dict:
    file_path = get_dashboard_file_path()
    assert file_path.exists(), f"Dashboard JSON must exist at {file_path}"
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_dashboard_file_exists_and_is_valid_json() -> None:
    """
    Verify monitoring/grafana/dashboards/sentinelgraph-operations.json exists and is valid JSON.
    """
    dashboard = load_dashboard_json()
    assert isinstance(dashboard, dict)
    assert dashboard.get("title") == "SentinelGraph AI — Operations Dashboard"
    assert "panels" in dashboard
    assert len(dashboard["panels"]) >= 8


# ============================================================================
# 2. Required Panels & Metadata Tests
# ============================================================================


def test_required_panels_exist() -> None:
    """
    Verify that all 8 required operational telemetry panels exist in the dashboard:
    1. HTTP request rate
    2. HTTP 5xx error rate
    3. HTTP P95 latency
    4. Gemini request rate
    5. Gemini error rate
    6. Gemini P95 latency
    7. Gemini token usage
    8. Readiness / availability signal
    """
    dashboard = load_dashboard_json()
    panels = dashboard["panels"]

    panel_titles = {p.get("title") for p in panels if p.get("type") != "row"}

    expected_titles = {
        "HTTP Request Rate",
        "HTTP 5xx Error Rate",
        "HTTP P95 Latency",
        "Gemini Request Rate",
        "Gemini Error Rate",
        "Gemini P95 Latency",
        "Gemini Token Usage",
        "Readiness Availability",
    }

    for title in expected_titles:
        assert title in panel_titles, f"Missing required panel: '{title}'"


def test_panels_have_units_and_descriptions() -> None:
    """
    Verify every operational panel defines a title, description, and valid unit.
    """
    dashboard = load_dashboard_json()
    data_panels = [p for p in dashboard["panels"] if p.get("type") != "row"]

    for panel in data_panels:
        title = panel.get("title")
        assert title, "Panel missing title"
        assert panel.get("description"), f"Panel '{title}' missing description"
        assert len(panel.get("targets", [])) > 0, f"Panel '{title}' has no targets"

        unit = panel.get("fieldConfig", {}).get("defaults", {}).get("unit")
        assert unit is not None, f"Panel '{title}' missing unit configuration"


# ============================================================================
# 3. PromQL Queries & Metric Reference Tests
# ============================================================================


def test_queries_reference_existing_application_metrics() -> None:
    """
    Verify that all PromQL target expressions in panels reference only verified
    application metrics defined in app/core/metrics.py.
    """
    dashboard = load_dashboard_json()

    known_metrics = {
        "http_requests_total",
        "http_request_duration_seconds",
        "http_request_duration_seconds_bucket",
        "http_request_duration_seconds_count",
        "http_request_duration_seconds_sum",
        "llm_requests_total",
        "llm_request_duration_seconds",
        "llm_request_duration_seconds_bucket",
        "llm_request_duration_seconds_count",
        "llm_request_duration_seconds_sum",
        "llm_tokens_total",
    }

    # Verify metrics in module
    assert hasattr(core_metrics_module, "http_requests_total")
    assert hasattr(core_metrics_module, "http_request_duration_seconds")
    assert hasattr(core_metrics_module, "llm_requests_total")
    assert hasattr(core_metrics_module, "llm_request_duration_seconds")
    assert hasattr(core_metrics_module, "llm_tokens_total")

    promql_keywords = {"sum", "rate", "histogram_quantile", "by", "vector", "or"}

    data_panels = [p for p in dashboard["panels"] if p.get("type") != "row"]
    for panel in data_panels:
        for target in panel.get("targets", []):
            expr = target.get("expr", "")
            assert expr, f"Target in panel '{panel.get('title')}' has empty expr"

            tokens = re.findall(r"\b([a-z_][a-z0-9_]*)\s*(?:\{|\[)", expr)
            used_metrics = [t for t in tokens if t not in promql_keywords and not t.isdigit()]

            assert len(used_metrics) > 0, f"No metric found in expr: {expr}"
            for m in used_metrics:
                assert m in known_metrics, f"Unknown metric '{m}' in panel '{panel.get('title')}'"


# ============================================================================
# 4. Datasource Parameterization & PII Safety Tests
# ============================================================================


def test_datasource_is_parameterized_and_not_hardcoded() -> None:
    """
    Verify datasource uses template variable (${DS_PROMETHEUS}) and contains
    no hardcoded localhost, 127.0.0.1, or machine-specific URLs.
    """
    raw_content = get_dashboard_file_path().read_text(encoding="utf-8")

    assert "localhost" not in raw_content.lower()
    assert "127.0.0.1" not in raw_content
    assert "http://" not in raw_content
    assert "https://" not in raw_content

    dashboard = load_dashboard_json()
    assert "templating" in dashboard
    template_vars = {v.get("name"): v for v in dashboard["templating"].get("list", [])}
    assert "DS_PROMETHEUS" in template_vars
    assert template_vars["DS_PROMETHEUS"].get("type") == "datasource"
    assert template_vars["DS_PROMETHEUS"].get("query") == "prometheus"


def test_no_pii_or_dynamic_identifiers_in_dashboard() -> None:
    """
    Verify dashboard JSON does not contain PII labels or dynamic fraud identifiers.
    """
    raw_content = get_dashboard_file_path().read_text(encoding="utf-8")
    forbidden_terms = ["phone=", "upi=", "email=", "bank_account=", "victim=", "case_reference="]

    for term in forbidden_terms:
        assert term not in raw_content, f"PII or dynamic identifier '{term}' found in dashboard JSON"
