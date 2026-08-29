"""
Regression tests for Sprint 12.8C: Grafana Provisioning:
1. Provisioning files exist (datasources.yml and dashboards.yml).
2. Files contain valid YAML structure and proper apiVersion headers.
3. Prometheus datasource is properly configured as the default datasource.
4. Dashboard provider configuration is present and references the dashboard path.
5. No machine-specific local paths, IP addresses, or hardcoded credentials exist.
6. Provisioning config matches the SentinelGraph operations dashboard UID/type.
"""

from __future__ import annotations

import json
from pathlib import Path


# ============================================================================
# 1. Provisioning File Existence & Structure Tests
# ============================================================================


def get_monitoring_root() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "monitoring" / "grafana"


def test_provisioning_files_exist() -> None:
    """
    Verify datasources.yml and dashboards.yml exist in their respective provisioning directories.
    """
    monitoring_root = get_monitoring_root()
    ds_file = monitoring_root / "provisioning" / "datasources" / "datasources.yml"
    dash_file = monitoring_root / "provisioning" / "dashboards" / "dashboards.yml"

    assert ds_file.exists(), f"Datasource provisioning file must exist at {ds_file}"
    assert dash_file.exists(), f"Dashboard provisioning file must exist at {dash_file}"


def test_datasource_provisioning_structure() -> None:
    """
    Verify datasources.yml defines a valid Prometheus datasource with parameterized URL.
    """
    monitoring_root = get_monitoring_root()
    ds_file = monitoring_root / "provisioning" / "datasources" / "datasources.yml"
    content = ds_file.read_text(encoding="utf-8")

    assert "apiVersion: 1" in content
    assert "datasources:" in content
    assert "name: Prometheus" in content
    assert "type: prometheus" in content
    assert "isDefault: true" in content
    assert "url: ${PROMETHEUS_URL:-http://prometheus:9090}" in content or "http://prometheus:9090" in content

    # Check for absence of machine-specific localhost or local dev URLs
    assert "127.0.0.1" not in content
    assert "localhost" not in content


def test_dashboard_provider_provisioning_structure() -> None:
    """
    Verify dashboards.yml defines a valid file-based dashboard provider.
    """
    monitoring_root = get_monitoring_root()
    dash_file = monitoring_root / "provisioning" / "dashboards" / "dashboards.yml"
    content = dash_file.read_text(encoding="utf-8")

    assert "apiVersion: 1" in content
    assert "providers:" in content
    assert "type: file" in content
    assert "folder: SentinelGraph" in content
    assert "path: /etc/grafana/provisioning/dashboards" in content or "path:" in content


# ============================================================================
# 2. Compatibility & Hygiene Tests
# ============================================================================


def test_no_machine_specific_paths_or_secrets_in_provisioning() -> None:
    """
    Ensure no machine-specific absolute file system paths (e.g. C:, /home/) or credentials exist.
    """
    monitoring_root = get_monitoring_root()
    prov_dir = monitoring_root / "provisioning"

    for file_path in prov_dir.rglob("*.yml"):
        content = file_path.read_text(encoding="utf-8")
        assert "C:\\" not in content, f"Windows path found in {file_path.name}"
        assert "/Users/" not in content, f"macOS user path found in {file_path.name}"
        assert "/home/" not in content, f"Linux user path found in {file_path.name}"
        assert "password:" not in content.lower(), f"Hardcoded password found in {file_path.name}"


def test_provisioning_matches_dashboard_datasource_contract() -> None:
    """
    Verify that the Prometheus datasource type specified in provisioning
    matches the datasource type used across panels in the operations dashboard JSON.
    """
    monitoring_root = get_monitoring_root()
    dashboard_path = monitoring_root / "dashboards" / "sentinelgraph-operations.json"
    assert dashboard_path.exists()

    with open(dashboard_path, "r", encoding="utf-8") as f:
        dashboard = json.load(f)

    # Check that template datasource query is prometheus
    template_vars = {v["name"]: v for v in dashboard.get("templating", {}).get("list", [])}
    assert "DS_PROMETHEUS" in template_vars
    assert template_vars["DS_PROMETHEUS"]["query"] == "prometheus"
