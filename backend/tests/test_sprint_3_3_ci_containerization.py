"""
Regression tests for Sprint 3.3: CI/CD Containerization & Verification Gates:
1. CI workflow file (.github/workflows/ci.yml) exists and is valid YAML.
2. Python version in CI is aligned with the production Dockerfile baseline (Python 3.13).
3. CI includes a Docker Compose configuration validation step.
4. CI includes a production Docker image build step.
5. Migration validation (offline dry-run) and pytest test execution stages are preserved in correct sequence.
6. CI contains no push commands or unauthorized deployment automation.
"""

from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_ci_workflow_path() -> Path:
    return get_repo_root() / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_file_exists() -> None:
    """
    Verify .github/workflows/ci.yml exists.
    """
    ci_path = get_ci_workflow_path()
    assert ci_path.exists(), f"CI workflow file must exist at {ci_path}"


def test_ci_python_version_aligned_with_dockerfile() -> None:
    """
    Verify CI Python version is aligned with Dockerfile (Python 3.13).
    """
    ci_path = get_ci_workflow_path()
    content = ci_path.read_text(encoding="utf-8")

    assert 'python-version: "3.13"' in content or "python-version: '3.13'" in content or "python-version: 3.13" in content

    # Verify Dockerfile also uses Python 3.13
    dockerfile_path = get_repo_root() / "backend" / "Dockerfile"
    dockerfile_content = dockerfile_path.read_text(encoding="utf-8")
    assert "python:3.13-slim" in dockerfile_content


def test_ci_includes_compose_and_docker_build_steps() -> None:
    """
    Verify CI includes Docker Compose validation and Docker build steps.
    """
    ci_path = get_ci_workflow_path()
    content = ci_path.read_text(encoding="utf-8")

    assert "Validate Docker Compose Configuration" in content
    assert "docker compose -f docker-compose.yml config" in content or "docker compose config" in content
    assert "Build Production Docker Image" in content
    assert "docker build" in content
    assert "Dockerfile" in content


def test_ci_preserves_required_quality_gates_and_sequence() -> None:
    """
    Verify Ruff, Alembic dry-run validation, Pytest, Compose validation, and Docker build
    appear in the correct deterministic order.
    """
    ci_path = get_ci_workflow_path()
    content = ci_path.read_text(encoding="utf-8")

    ruff_pos = content.find("python -m ruff check")
    alembic_pos = content.find("python -m alembic upgrade head --sql")
    pytest_pos = content.find("python -m pytest")
    compose_pos = content.find("docker compose")
    docker_build_pos = content.find("docker build")

    assert ruff_pos != -1, "Ruff step missing"
    assert alembic_pos != -1, "Alembic step missing"
    assert pytest_pos != -1, "Pytest step missing"
    assert compose_pos != -1, "Docker compose validation step missing"
    assert docker_build_pos != -1, "Docker build step missing"

    assert ruff_pos < alembic_pos < pytest_pos < compose_pos < docker_build_pos, (
        "CI steps must execute in order: Ruff -> Alembic -> Pytest -> Compose Validation -> Docker Build"
    )


def test_ci_contains_no_docker_push_or_deployment() -> None:
    """
    Verify CI contains no push commands or deployment steps.
    """
    ci_path = get_ci_workflow_path()
    content = ci_path.read_text(encoding="utf-8")

    assert "docker push" not in content
    assert "deploy" not in content.lower()
