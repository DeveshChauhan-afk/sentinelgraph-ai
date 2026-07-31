"""
Unit tests for PromptBuilder & Prompt Template Architecture (Sprint 9 Phase 3.5 Refinements).

Validates strongly typed prompt sections, SHA-256 prompt fingerprinting, template registry resolution,
prompt metrics & diagnostics, explicit multi-versioning, provider independence, output schema validation,
prompt ordering stability, and validation rule enforcement.
"""

from __future__ import annotations


import pytest
from pydantic import ValidationError

from app.prompts.templates import (
    PromptTemplateRegistry,
    get_executive_report_template,
)
from app.schemas.prompt import (
    DeveloperInstructions,
    ExpectedReportStructure,
    PromptConstraints,
    PromptMetadata,
    PromptMetrics,
    PromptRequest,
    SerializedContext,
    SystemPrompt,
)
from app.services.investigation_summary_service import InvestigationSummaryService
from app.services.prompt_builder import PromptBuilder
from app.services.report_context_builder import ReportContextBuilder


@pytest.fixture
def sample_report_context():
    """
    Fixture creating a representative InvestigationReportContext for prompt tests.
    """
    summary_service = InvestigationSummaryService()
    summary = summary_service.create_summary_from_outputs(target_value="+919876543210", target_type="phone")

    context_builder = ReportContextBuilder()
    return context_builder.build_report_context(summary)


def test_prompt_sections_typed_models(sample_report_context):
    """
    Test that PromptRequest contains strongly typed section models.
    """
    builder = PromptBuilder()
    request = builder.build_prompt_request(sample_report_context)

    assert isinstance(request, PromptRequest)
    assert isinstance(request.system_prompt, SystemPrompt)
    assert isinstance(request.developer_instructions, DeveloperInstructions)
    assert isinstance(request.context, SerializedContext)
    assert isinstance(request.expected_structure, ExpectedReportStructure)
    assert isinstance(request.constraints, PromptConstraints)


def test_prompt_fingerprint_determinism(sample_report_context):
    """
    Test SHA-256 prompt hash fingerprint generation and 100% determinism.
    """
    builder = PromptBuilder()

    req1 = builder.build_prompt_request(sample_report_context)
    req2 = builder.build_prompt_request(sample_report_context)

    assert len(req1.metadata.prompt_hash) == 64
    assert req1.metadata.prompt_hash == req2.metadata.prompt_hash


def test_prompt_metrics_and_diagnostics(sample_report_context):
    """
    Test prompt diagnostics and context compression metrics.
    """
    builder = PromptBuilder()
    request = builder.build_prompt_request(sample_report_context)

    metrics = request.metadata.metrics
    assert isinstance(metrics, PromptMetrics)
    assert metrics.estimated_token_count > 0
    assert metrics.serialized_context_size_bytes > 0
    assert metrics.finding_count == len(sample_report_context.critical_findings)
    assert metrics.entity_count == len(sample_report_context.entity_highlights.highlights)


def test_template_registry_behavior(sample_report_context):
    """
    Test retrieving templates from PromptTemplateRegistry by identifier.
    """
    registry = PromptTemplateRegistry()
    builder = PromptBuilder(registry=registry)

    # Executive report
    req_exec = builder.build_prompt_request(sample_report_context, template_id="EXECUTIVE_INVESTIGATION_REPORT")
    assert req_exec.metadata.template_id == "EXECUTIVE_INVESTIGATION_REPORT"

    # Law enforcement report
    req_le = builder.build_prompt_request(sample_report_context, template_id="LAW_ENFORCEMENT_REPORT")
    assert req_le.metadata.template_id == "LAW_ENFORCEMENT_REPORT"


def test_explicit_multi_versioning(sample_report_context):
    """
    Test explicit independent version metadata tracking.
    """
    builder = PromptBuilder()
    request = builder.build_prompt_request(sample_report_context)

    meta = request.metadata
    assert meta.prompt_version == "1.0"
    assert meta.template_version == "1.0"
    assert meta.report_context_version == sample_report_context.metadata.report_context_version
    assert meta.summary_version == sample_report_context.metadata.generated_from_summary_version


def test_provider_independence(sample_report_context):
    """
    Test that PromptRequest uses generic provider-independent terminology.
    """
    builder = PromptBuilder()
    request = builder.build_prompt_request(sample_report_context)

    full_prompt = request.full_prompt
    assert "LLM SYSTEM ROLE" in full_prompt
    assert "LLM INSTRUCTIONS" in full_prompt


def test_output_schema_structure(sample_report_context):
    """
    Test structured output contract definition for Phase 4 parsing.
    """
    builder = PromptBuilder()
    request = builder.build_prompt_request(sample_report_context)

    sections = request.expected_structure.sections
    assert len(sections) == 8
    section_ids = [s.section_id for s in sections]
    assert "EXECUTIVE_SUMMARY" in section_ids
    assert "KEY_FINDINGS" in section_ids
    assert "RECOMMENDATIONS" in section_ids


def test_prompt_validation_failures():
    """
    Test deterministic prompt validation raises ValueError on empty or invalid components.
    """
    builder = PromptBuilder()

    # System prompt without operating rules
    invalid_sys = SystemPrompt(role="Test Role", operating_rules=())
    dev_inst = DeveloperInstructions(citation_instructions=("Cite items",), style_guidelines=("Be clear",))
    context = SerializedContext(json_data='{"test": 1}', size_bytes=10)
    struct = get_executive_report_template().expected_structure
    constraints = PromptConstraints()
    meta = PromptMetadata(prompt_hash="dummy")

    invalid_req = PromptRequest(
        metadata=meta,
        system_prompt=invalid_sys,
        developer_instructions=dev_inst,
        context=context,
        expected_structure=struct,
        constraints=constraints,
    )

    with pytest.raises(ValueError, match="operating_rules are missing"):
        builder.validate_prompt_request(invalid_req)


def test_immutability(sample_report_context):
    """
    Test that PromptRequest and all sub-models are frozen and read-only.
    """
    builder = PromptBuilder()
    request = builder.build_prompt_request(sample_report_context)

    with pytest.raises((ValidationError, AttributeError, TypeError)):
        request.metadata = PromptMetadata(prompt_hash="hacked")

    with pytest.raises((ValidationError, AttributeError, TypeError)):
        request.constraints.temperature = 1.5


@pytest.mark.asyncio
async def test_async_prompt_builder_support(sample_report_context):
    """
    Test async build_prompt_request_async method.
    """
    builder = PromptBuilder()
    request = await builder.build_prompt_request_async(sample_report_context)
    assert request.metadata.model_name == "gemini-3.5-flash-lite"
    assert len(request.metadata.prompt_hash) == 64
