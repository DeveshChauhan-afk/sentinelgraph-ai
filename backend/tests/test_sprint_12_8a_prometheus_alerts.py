"""
Regression tests for Sprint 12.8A: Prometheus Alert Rules:
1. Alert rules file exists and parses properly.
2. Structure adheres to standard Prometheus Alertmanager rule schema (groups, rules, alert, expr, for, labels, annotations).
3. All metric names referenced in expressions exist in app/core/metrics.py.
4. Expressions use bounded thresholds and required `for` evaluation durations.
5. No raw PII or unbounded dynamic labels are referenced in alert expressions.
6. Alert severities, summaries, and descriptions are populated.
"""

from __future__ import annotations

from pathlib import Path
import re

from app.core import metrics as core_metrics_module


# ============================================================================
# 1. Alert Rule File Existence & Parsing
# ============================================================================


def get_alerts_file_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "monitoring" / "prometheus" / "alerts.yml"


def load_alerts_text() -> str:
    file_path = get_alerts_file_path()
    assert file_path.exists(), f"Alerts rule file must exist at {file_path}"
    return file_path.read_text(encoding="utf-8")


def parse_prometheus_rules_simple(content: str) -> list[dict]:
    """
    Parse Prometheus rules from YAML without third-party dependencies.
    Extracts each alert block with its alert name, expr, for, labels, and annotations.
    """
    rule_blocks = re.findall(
        r"-\s*alert:\s*([A-Za-z0-9_]+)\s*\n"
        r"(.*?)(?=\n\s*-\s*alert:|\Z)",
        content,
        re.DOTALL,
    )

    parsed_rules = []
    for alert_name, block in rule_blocks:
        rule_dict = {"alert": alert_name}

        # Extract expr (handles multi-line expressions)
        expr_match = re.search(r"expr:\s*>(.*?)(?=\n\s*(?:for|labels|annotations):)", block, re.DOTALL)
        if not expr_match:
            expr_match = re.search(r"expr:\s*(.*?)(?=\n\s*(?:for|labels|annotations):)", block, re.DOTALL)
        rule_dict["expr"] = expr_match.group(1).strip() if expr_match else ""

        # Extract for duration
        for_match = re.search(r"for:\s*([0-9]+[smhd])", block)
        rule_dict["for"] = for_match.group(1) if for_match else ""

        # Extract labels
        labels = {}
        labels_match = re.search(r"labels:\s*\n(.*?)(?=\n\s*annotations:|\Z)", block, re.DOTALL)
        if labels_match:
            for l_match in re.finditer(r"([a-z_]+):\s*([a-zA-Z0-9_\-]+)", labels_match.group(1)):
                labels[l_match.group(1)] = l_match.group(2)
        rule_dict["labels"] = labels

        # Extract annotations
        annotations = {}
        ann_match = re.search(r"annotations:\s*\n(.*?)(?=\n\s*-\s*alert:|\Z)", block, re.DOTALL)
        if ann_match:
            for a_match in re.finditer(r'([a-z_]+):\s*["\']?(.*?)["\']?\s*(?=\n\s*[a-z_]+:|\Z)', ann_match.group(1), re.DOTALL):
                annotations[a_match.group(1)] = a_match.group(2).strip()
        rule_dict["annotations"] = annotations

        parsed_rules.append(rule_dict)

    return parsed_rules


def test_alert_rule_file_exists_and_has_content() -> None:
    """
    Verify monitoring/prometheus/alerts.yml exists and contains groups and rules.
    """
    content = load_alerts_text()
    assert "groups:" in content
    assert "name: sentinelgraph_alerts" in content
    assert "- alert:" in content


# ============================================================================
# 2. Prometheus Rule Schema & Metadata Tests
# ============================================================================


def test_prometheus_rule_structure() -> None:
    """
    Verify all alert rules define mandatory Prometheus fields:
    alert, expr, for, labels (severity, service), annotations (summary, description).
    """
    content = load_alerts_text()
    rules = parse_prometheus_rules_simple(content)
    assert len(rules) >= 4, f"Expected at least 4 alert rules, found {len(rules)}"

    alert_names = set()

    for rule in rules:
        alert_name = rule["alert"]
        assert alert_name, "Rule must have an alert name"
        assert rule["expr"], f"Rule {alert_name} missing expr"
        assert rule["for"], f"Rule {alert_name} missing for duration"
        assert rule["labels"], f"Rule {alert_name} missing labels"
        assert rule["annotations"], f"Rule {alert_name} missing annotations"

        alert_names.add(alert_name)

        # Verify labels
        labels = rule["labels"]
        assert "severity" in labels
        assert labels["severity"] in ("critical", "warning", "info")
        assert labels.get("service") == "sentinelgraph-backend"

        # Verify annotations
        annotations = rule["annotations"]
        assert "summary" in annotations
        assert "description" in annotations
        assert len(annotations["summary"]) > 5
        assert len(annotations["description"]) > 10

        # Verify `for` duration is formatted appropriately (e.g., 2m, 5m, 10m)
        assert re.match(r"^\d+[smhd]$", rule["for"]), f"Invalid for duration format: {rule['for']}"

    # Verify key required alert types exist
    assert "HighHttp5xxErrorRate" in alert_names
    assert "ElevatedHttpRequestLatency" in alert_names
    assert "HighLlmErrorRate" in alert_names
    assert "ElevatedLlmRequestLatency" in alert_names
    assert "ReadinessProbeFailing" in alert_names


# ============================================================================
# 3. Metric Name & PII Validation Tests
# ============================================================================


def test_alert_rules_reference_existing_application_metrics() -> None:
    """
    Verify that every metric name referenced in the alert expressions
    actually exists and is defined in app/core/metrics.py.
    """
    content = load_alerts_text()
    rules = parse_prometheus_rules_simple(content)

    # Collect known metrics from backend/app/core/metrics.py
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

    for rule in rules:
        expr = rule["expr"]
        tokens = re.findall(r"\b([a-z_][a-z0-9_]*)\s*(?:\{|\[)", expr)
        used_metrics = [t for t in tokens if t not in promql_keywords and not t.isdigit()]

        assert len(used_metrics) > 0, f"No metric found in expr: {expr}"
        for m in used_metrics:
            assert m in known_metrics, f"Unknown metric '{m}' referenced in alert {rule['alert']}"


def test_alert_expressions_contain_no_pii_or_unbounded_labels() -> None:
    """
    Verify that alert expressions do not filter on or reference PII labels
    such as phone numbers, bank accounts, UPI IDs, names, or victim details.
    """
    content = load_alerts_text()
    rules = parse_prometheus_rules_simple(content)
    forbidden_labels = {"phone", "upi", "email", "bank_account", "person", "victim", "case_reference", "target"}

    for rule in rules:
        expr = rule["expr"]
        for forbidden in forbidden_labels:
            assert f"{forbidden}=" not in expr, f"PII label '{forbidden}' detected in alert {rule['alert']}"
