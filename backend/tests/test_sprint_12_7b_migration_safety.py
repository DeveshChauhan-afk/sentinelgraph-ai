"""
Regression tests for Sprint 12.7B: Migration Execution Safety:
1. Migration revision chain linearity and single-head determinism.
2. Upgrade and downgrade function presence across all migration versions.
3. Decoupling of Alembic migrations from FastAPI startup lifecycle (preventing concurrent DDL race conditions).
4. Alembic runtime configuration and SYNC_DATABASE_URL injection.
5. Online migration NullPool configuration and transaction boundary safety.
6. Target metadata binding to Base.metadata containing all application tables.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import settings
import app.core.events as events_module
from app.db.base import Base


# ============================================================================
# 1. Migration Chain Linearity & Determinism Tests
# ============================================================================


def test_alembic_revisions_chain_has_single_head_and_single_base() -> None:
    """
    Verify that the Alembic migration history forms a clean, deterministic,
    linear DAG with exactly 1 head and 1 base (no branches, splits, or merge conflicts).
    """
    backend_root = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_root / "alembic.ini"
    assert alembic_ini_path.exists(), "alembic.ini must exist in backend directory"

    config = Config(str(alembic_ini_path))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 migration head, found {len(heads)}: {heads}"
    assert heads[0] == "e7c2a19d4b8f"

    base = script.get_base()
    assert base == "3d3cf359c2a1"

    revisions = list(script.walk_revisions())
    assert len(revisions) == 2

    # Linear link verification: head down_revision points to base
    head_rev = script.get_revision(heads[0])
    assert head_rev is not None
    assert head_rev.down_revision == "3d3cf359c2a1"


def test_all_migration_versions_define_upgrade_and_downgrade() -> None:
    """
    Verify every version script in alembic/versions exports valid upgrade() and downgrade() functions.
    """
    backend_root = Path(__file__).resolve().parent.parent
    versions_dir = backend_root / "alembic" / "versions"
    assert versions_dir.exists()

    migration_files = [f for f in versions_dir.glob("*.py") if not f.name.startswith("__")]
    assert len(migration_files) >= 2

    for mig_file in migration_files:
        module_dict: dict = {}
        with open(mig_file, "r", encoding="utf-8") as f:
            code = compile(f.read(), str(mig_file), "exec")
            exec(code, module_dict)  # noqa: S102

        assert "upgrade" in module_dict, f"Missing upgrade() in {mig_file.name}"
        assert "downgrade" in module_dict, f"Missing downgrade() in {mig_file.name}"
        assert callable(module_dict["upgrade"]), f"upgrade in {mig_file.name} must be callable"
        assert callable(module_dict["downgrade"]), f"downgrade in {mig_file.name} must be callable"
        assert inspect.isfunction(module_dict["upgrade"])
        assert inspect.isfunction(module_dict["downgrade"])


# ============================================================================
# 2. Decoupled Application Startup & Concurrency Safety Tests
# ============================================================================


def test_fastapi_startup_lifecycle_does_not_embed_alembic_migrations() -> None:
    """
    Verify that application startup in app/core/events.py does NOT automatically
    execute Alembic migrations. This guarantees that multi-worker or multi-replica
    FastAPI deployments never execute concurrent DDL migrations or race on alembic_version.
    """
    startup_func = getattr(events_module, "startup")
    source_code = inspect.getsource(startup_func)

    assert "alembic" not in source_code.lower()
    assert "upgrade" not in source_code.lower()
    assert "run_migrations" not in source_code.lower()


# ============================================================================
# 3. Alembic Runtime Configuration & Transactional Safety Tests
# ============================================================================


def test_alembic_env_source_configures_metadata_and_sync_url() -> None:
    """
    Verify that alembic/env.py binds target_metadata to Base.metadata and
    dynamically sets sqlalchemy.url from settings.SYNC_DATABASE_URL.
    """
    backend_root = Path(__file__).resolve().parent.parent
    env_py_path = backend_root / "alembic" / "env.py"
    assert env_py_path.exists()

    env_source = env_py_path.read_text(encoding="utf-8")

    assert 'config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)' in env_source
    assert "target_metadata = Base.metadata" in env_source
    assert "poolclass=pool.NullPool" in env_source
    assert "context.begin_transaction()" in env_source
    assert "context.run_migrations()" in env_source
    assert "compare_type=True" in env_source


def test_base_metadata_contains_application_tables() -> None:
    """
    Verify SQLAlchemy Base metadata contains all registered models for autogenerate comparison.
    """
    import app.models.incident  # noqa: F401

    table_names = set(Base.metadata.tables.keys())
    assert "incidents" in table_names
    assert "id" in Base.metadata.tables["incidents"].columns
    assert "case_reference" in Base.metadata.tables["incidents"].columns


def test_settings_sync_database_url_validity() -> None:
    """
    Verify settings.SYNC_DATABASE_URL produces valid psycopg2 PostgreSQL connection string.
    """
    sync_url = settings.SYNC_DATABASE_URL
    assert sync_url.startswith("postgresql+psycopg2://")
    assert f"@{settings.DATABASE_HOST}" in sync_url
    assert f":{settings.DATABASE_PORT}" in sync_url
    assert f"/{settings.DATABASE_NAME}" in sync_url
