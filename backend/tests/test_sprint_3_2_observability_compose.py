"""
Regression tests for Sprint 3.2: Observability & Docker Compose Consolidation:
1. Prometheus configuration file (prometheus.yml) exists and has valid structure.
2. Prometheus scrape configuration targets the FastAPI API metrics endpoint (api:8000/metrics).
3. Prometheus rule configuration includes the alerts.yml rule file.
4. Docker Compose configuration includes api, postgres, prometheus, and grafana services.
5. Docker Compose services define appropriate ports, dependencies, volumes, and healthchecks.
6. Persistent named volumes exist for postgres, prometheus, and grafana.
"""

from __future__ import annotations

from pathlib import Path
import re


# ============================================================================
# Helper Functions
# ============================================================================


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_prometheus_config_path() -> Path:
    return get_repo_root() / "monitoring" / "prometheus" / "prometheus.yml"


def get_compose_file_path() -> Path:
    return get_repo_root() / "backend" / "docker-compose.yml"


# ============================================================================
# 1. Prometheus Scrape Configuration Tests
# ============================================================================


def test_prometheus_config_file_exists() -> None:
    """
    Verify monitoring/prometheus/prometheus.yml exists.
    """
    prom_path = get_prometheus_config_path()
    assert prom_path.exists(), f"Prometheus config file must exist at {prom_path}"


def test_prometheus_config_structure_and_intervals() -> None:
    """
    Verify prometheus.yml contains valid global settings, rule_files, and scrape_configs.
    """
    prom_path = get_prometheus_config_path()
    content = prom_path.read_text(encoding="utf-8")

    assert "global:" in content
    assert "scrape_interval:" in content
    assert "evaluation_interval:" in content
    assert "rule_files:" in content
    assert "scrape_configs:" in content


def test_prometheus_config_references_alerts_rule_file() -> None:
    """
    Verify prometheus.yml references alerts.yml in rule_files.
    """
    prom_path = get_prometheus_config_path()
    content = prom_path.read_text(encoding="utf-8")

    assert "alerts.yml" in content
    # Verify the referenced alerts file actually exists in repository
    alerts_path = get_repo_root() / "monitoring" / "prometheus" / "alerts.yml"
    assert alerts_path.exists(), f"Referenced alerts rule file must exist at {alerts_path}"


def test_prometheus_config_scrapes_api_metrics() -> None:
    """
    Verify prometheus.yml configures scraping for the FastAPI api:8000 /metrics endpoint.
    """
    prom_path = get_prometheus_config_path()
    content = prom_path.read_text(encoding="utf-8")

    assert "job_name: \"sentinelgraph-backend\"" in content or "job_name: 'sentinelgraph-backend'" in content or "sentinelgraph-backend" in content
    assert "api:8000" in content
    assert "/metrics" in content


# ============================================================================
# 2. Docker Compose Service & Architecture Tests
# ============================================================================


def test_docker_compose_file_exists() -> None:
    """
    Verify backend/docker-compose.yml exists.
    """
    compose_path = get_compose_file_path()
    assert compose_path.exists(), f"docker-compose.yml must exist at {compose_path}"


def test_docker_compose_defines_all_required_services() -> None:
    """
    Verify docker-compose.yml defines api, postgres, prometheus, and grafana services.
    """
    compose_path = get_compose_file_path()
    content = compose_path.read_text(encoding="utf-8")

    # Service definitions
    assert re.search(r"^\s*api:\s*$", content, re.MULTILINE)
    assert re.search(r"^\s*postgres:\s*$", content, re.MULTILINE)
    assert re.search(r"^\s*prometheus:\s*$", content, re.MULTILINE)
    assert re.search(r"^\s*grafana:\s*$", content, re.MULTILINE)


def test_docker_compose_prometheus_service_configuration() -> None:
    """
    Verify prometheus service has correct image, ports, mounts, and dependencies.
    """
    compose_path = get_compose_file_path()
    content = compose_path.read_text(encoding="utf-8")

    assert "prom/prometheus:" in content
    assert '"9090:9090"' in content or "'9090:9090'" in content or "9090:9090" in content
    assert "prometheus.yml" in content
    assert "alerts.yml" in content
    assert "prometheus_data" in content


def test_docker_compose_grafana_service_configuration() -> None:
    """
    Verify grafana service has correct image, ports, mounts, and dependencies.
    """
    compose_path = get_compose_file_path()
    content = compose_path.read_text(encoding="utf-8")

    assert "grafana/grafana:" in content
    assert '"3000:3000"' in content or "'3000:3000'" in content or "3000:3000" in content
    assert "datasources.yml" in content
    assert "dashboards.yml" in content
    assert "sentinelgraph-operations.json" in content
    assert "grafana_data" in content


def test_docker_compose_persistent_volumes_defined() -> None:
    """
    Verify all 3 persistent named volumes are declared: postgres_data, prometheus_data, grafana_data.
    """
    compose_path = get_compose_file_path()
    content = compose_path.read_text(encoding="utf-8")

    assert "volumes:" in content
    assert "postgres_data:" in content
    assert "prometheus_data:" in content
    assert "grafana_data:" in content


def test_docker_compose_healthchecks_configured() -> None:
    """
    Verify healthchecks are configured for database and observability services.
    """
    compose_path = get_compose_file_path()
    content = compose_path.read_text(encoding="utf-8")

    assert "pg_isready" in content
    assert "http://localhost:9090/-/healthy" in content
    assert "http://localhost:3000/api/health" in content
