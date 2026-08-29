"""
Regression tests for Sprint 12.7A: Deployment Hardening Audit:
1. Production container entrypoint, non-root user execution, and port exposure.
2. Configuration/secrets validation and SecretStr masking.
3. PostgreSQL connection URL generation (asyncpg for runtime, psycopg2 for Alembic).
4. Alembic migration operational configuration and script integrity.
5. Container orchestration health endpoints (/health/live and /health/ready).
6. Docker configuration file exclusion (.dockerignore secret/cache protection).
7. Default production configuration safety (DEBUG=False).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.api.health import get_health_service
from app.core.config import Settings
from app.core.health.models import DependencyHealth, HealthStatus
from app.core.health.service import HealthService
from app.main import app

client = TestClient(app)


# ============================================================================
# 1. Dockerfile & .dockerignore Static Hardening Tests
# ============================================================================


def test_dockerfile_uses_non_root_user_and_production_command() -> None:
    """
    Verify Dockerfile follows production container best practices:
    - Multi-stage build (builder + runner)
    - Runs as non-root user (appuser)
    - Exposes port 8000
    - Uses production uvicorn command without --reload
    """
    dockerfile_path = Path(__file__).resolve().parent.parent / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist in backend root"

    content = dockerfile_path.read_text(encoding="utf-8")

    assert "FROM python:3.13-slim AS builder" in content
    assert "FROM python:3.13-slim AS runner" in content
    assert "USER appuser" in content
    assert "EXPOSE 8000" in content
    assert "CMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]" in content
    assert "--reload" not in content


def test_dockerignore_excludes_secrets_and_development_artifacts() -> None:
    """
    Verify .dockerignore excludes sensitive secrets, virtual environments,
    test files, and bytecode caches from the container build context.
    """
    dockerignore_path = Path(__file__).resolve().parent.parent / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist in backend root"

    content = dockerignore_path.read_text(encoding="utf-8")
    lines = {line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")}

    # Secrets
    assert ".env" in lines
    assert ".env.*" in lines
    # Caches
    assert "__pycache__" in lines
    assert ".pytest_cache" in lines
    assert ".ruff_cache" in lines
    # Virtual environments
    assert ".venv" in lines
    assert "venv" in lines
    # Tests and logs
    assert "tests" in lines
    assert "logs" in lines


# ============================================================================
# 2. Configuration & Secrets Hardening Tests
# ============================================================================


def test_settings_validates_required_secrets_and_types() -> None:
    """
    Verify Settings enforces mandatory fields and protects secrets as SecretStr.
    """
    # Missing all mandatory variables should raise ValidationError
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}
        assert "SECRET_KEY" in missing_fields
        assert "DATABASE_PASSWORD" in missing_fields
        assert "NEO4J_PASSWORD" in missing_fields
        assert "GEMINI_API_KEY" in missing_fields

    # Valid base dictionary with all required fields
    valid_base = {
        "SECRET_KEY": "test-key",
        "DATABASE_HOST": "localhost",
        "DATABASE_NAME": "test_db",
        "DATABASE_USER": "test_user",
        "DATABASE_PASSWORD": "test_password",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "test_password",
        "GEMINI_API_KEY": "test_api_key",
    }

    # Verify each required secret individually raises ValidationError when omitted
    for required_secret in ("SECRET_KEY", "DATABASE_PASSWORD", "NEO4J_PASSWORD", "GEMINI_API_KEY"):
        env_without_secret = {k: v for k, v in valid_base.items() if k != required_secret}
        with patch.dict(os.environ, env_without_secret, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            missing_fields = {e["loc"][0] for e in exc_info.value.errors()}
            assert required_secret in missing_fields, f"Expected ValidationError for missing {required_secret}"


def test_settings_secret_values_are_masked() -> None:
    """
    Verify SecretStr values are never rendered in plaintext in str() representation.
    """
    config = Settings(
        SECRET_KEY="super-secret-key-1234",
        DATABASE_HOST="postgres.internal",
        DATABASE_NAME="sentinel_prod",
        DATABASE_USER="sentinel_user",
        DATABASE_PASSWORD="db-secret-password-xyz",
        NEO4J_URI="bolt://neo4j.internal:7687",
        NEO4J_USERNAME="neo4j",
        NEO4J_PASSWORD="neo4j-secret-password-abc",
        GEMINI_API_KEY="gemini-secret-api-key-999",
        _env_file=None,
    )

    repr_str = str(config)
    assert "super-secret-key-1234" not in repr_str
    assert "db-secret-password-xyz" not in repr_str
    assert "neo4j-secret-password-abc" not in repr_str
    assert "gemini-secret-api-key-999" not in repr_str
    assert "**********" in repr_str or "SecretStr('**********')" in repr_str


def test_settings_default_debug_is_false() -> None:
    """
    Verify that default DEBUG setting is False for production safety.
    """
    config = Settings(
        SECRET_KEY="test",
        DATABASE_HOST="localhost",
        DATABASE_NAME="test",
        DATABASE_USER="test",
        DATABASE_PASSWORD="test",
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USERNAME="test",
        NEO4J_PASSWORD="test",
        GEMINI_API_KEY="test",
        _env_file=None,
    )
    assert config.DEBUG is False


def test_settings_database_urls_contain_correct_drivers() -> None:
    """
    Verify async and sync database connection URLs are generated with correct driver dialects.
    """
    config = Settings(
        SECRET_KEY="test",
        DATABASE_HOST="db.prod",
        DATABASE_PORT=5432,
        DATABASE_NAME="sentinel_db",
        DATABASE_USER="sentinel_app",
        DATABASE_PASSWORD="mypassword",
        NEO4J_URI="bolt://neo.prod:7687",
        NEO4J_USERNAME="neo4j",
        NEO4J_PASSWORD="neopassword",
        GEMINI_API_KEY="key",
        _env_file=None,
    )

    # Async URL for SQLAlchemy / asyncpg
    assert config.DATABASE_URL == "postgresql+asyncpg://sentinel_app:mypassword@db.prod:5432/sentinel_db"
    # Sync URL for Alembic / psycopg2
    assert config.SYNC_DATABASE_URL == "postgresql+psycopg2://sentinel_app:mypassword@db.prod:5432/sentinel_db"


def test_settings_validates_port_and_pool_boundaries() -> None:
    """
    Verify boundary validation on port and connection pool parameters.
    """
    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY="test",
            DATABASE_HOST="db.prod",
            DATABASE_PORT=70000,  # Invalid port > 65535
            DATABASE_NAME="test",
            DATABASE_USER="test",
            DATABASE_PASSWORD="test",
            NEO4J_URI="bolt://localhost:7687",
            NEO4J_USERNAME="test",
            NEO4J_PASSWORD="test",
            GEMINI_API_KEY="test",
            _env_file=None,
        )


# ============================================================================
# 3. Alembic Migration Operational Integrity Tests
# ============================================================================


def test_alembic_configuration_and_versions_exist() -> None:
    """
    Verify Alembic configuration file and migration revisions exist.
    """
    backend_root = Path(__file__).resolve().parent.parent
    alembic_ini = backend_root / "alembic.ini"
    alembic_dir = backend_root / "alembic"
    versions_dir = alembic_dir / "versions"

    assert alembic_ini.exists()
    assert (alembic_dir / "env.py").exists()
    assert versions_dir.exists()

    migration_files = list(versions_dir.glob("*.py"))
    assert len(migration_files) >= 2

    filenames = [f.name for f in migration_files]
    assert any("create_incidents_table" in name for name in filenames)
    assert any("add_case_reference_unique_constraint" in name for name in filenames)


# ============================================================================
# 4. Orchestration Health & Readiness Probes Tests
# ============================================================================


def test_liveness_probe_does_not_depend_on_external_databases() -> None:
    """
    Verify GET /health/live returns HTTP 200 without executing database queries,
    preventing pod restarts during transient downstream database latency.
    """
    with patch.object(HealthService, "check_dependencies") as mock_check:
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        mock_check.assert_not_called()


def test_readiness_probe_returns_503_when_critical_dependency_down() -> None:
    """
    Verify GET /health/ready returns HTTP 503 when a critical dependency (Postgres/Neo4j)
    is unhealthy, signaling load balancers and orchestrators to withhold ingress traffic.
    """
    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres",
            status=HealthStatus.UNHEALTHY,
            latency_ms=0.0,
            critical=True,
            message="Connection refused",
        ),
        "neo4j": DependencyHealth(
            name="neo4j",
            status=HealthStatus.HEALTHY,
            latency_ms=1.2,
            critical=True,
        ),
        "gemini": DependencyHealth(
            name="gemini",
            status=HealthStatus.HEALTHY,
            latency_ms=0.1,
            critical=False,
        ),
    }

    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    safe_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = safe_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["is_ready"] is False
        assert data["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()
