"""
Regression tests for Sprint 12.7C: Migration Release Verification:
1. CI workflow YAML configuration and presence of migration dry-run validation step.
2. Programmatic execution of offline migration SQL upgrade (head).
3. Programmatic execution of offline migration SQL downgrade (head:base).
4. SQL artifact verification (incidents table creation, enum definitions, unique constraint).
5. Error propagation when invalid revisions or broken migration graphs are supplied.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
import pytest


# ============================================================================
# 1. CI Workflow Configuration Tests
# ============================================================================


def test_ci_workflow_includes_migration_validation_step() -> None:
    """
    Verify .github/workflows/ci.yml includes an explicit migration validation step
    (python -m alembic upgrade head --sql) before running pytest.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    ci_workflow_path = repo_root / ".github" / "workflows" / "ci.yml"
    assert ci_workflow_path.exists(), "ci.yml workflow must exist"

    content = ci_workflow_path.read_text(encoding="utf-8")
    assert "Validate Database Migrations (Dry-Run)" in content
    assert "alembic upgrade head --sql" in content

    # Ensure migration validation appears before pytest
    alembic_pos = content.find("alembic upgrade head --sql")
    pytest_pos = content.find("python -m pytest")
    assert alembic_pos != -1
    assert pytest_pos != -1
    assert alembic_pos < pytest_pos, "Migration validation must run before pytest"


# ============================================================================
# 2. Offline Migration Upgrade & Downgrade SQL Generation Tests
# ============================================================================


def test_offline_migration_upgrade_generates_valid_sql(capsys: pytest.CaptureFixture[str]) -> None:
    """
    Verify alembic upgrade head --sql runs in offline mode without requiring
    live database infrastructure and generates the complete DDL schema.
    """
    backend_root = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_root / "alembic.ini"
    config = Config(str(alembic_ini_path))

    # Execute offline upgrade
    command.upgrade(config, "head", sql=True)
    captured = capsys.readouterr()
    generated_sql = captured.out

    assert "BEGIN;" in generated_sql
    assert "CREATE TABLE alembic_version" in generated_sql
    assert "CREATE TABLE incidents" in generated_sql
    assert "CREATE TYPE reporter_type_enum" in generated_sql
    assert "CREATE TYPE incident_source_enum" in generated_sql
    assert "uq_incidents_case_reference" in generated_sql
    assert "COMMIT;" in generated_sql


def test_offline_migration_downgrade_generates_valid_sql(capsys: pytest.CaptureFixture[str]) -> None:
    """
    Verify alembic downgrade head:base --sql runs in offline mode and drops
    the newly added constraints and tables symmetrically.
    """
    backend_root = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_root / "alembic.ini"
    config = Config(str(alembic_ini_path))

    # Execute offline downgrade from head to base
    command.downgrade(config, "head:base", sql=True)
    captured = capsys.readouterr()
    generated_sql = captured.out

    assert "BEGIN;" in generated_sql
    assert "ALTER TABLE incidents DROP CONSTRAINT uq_incidents_case_reference;" in generated_sql
    assert "COMMIT;" in generated_sql


def test_invalid_revision_in_offline_migration_raises_error() -> None:
    """
    Verify that an invalid revision string raises CommandError cleanly.
    """
    backend_root = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_root / "alembic.ini"
    config = Config(str(alembic_ini_path))

    with pytest.raises(CommandError):
        command.upgrade(config, "nonexistent_rev_123", sql=True)
