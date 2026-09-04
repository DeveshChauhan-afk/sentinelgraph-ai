"""
PromptBuilder Service Architecture (Sprint 9 Phase 3.5 Refinements).

Service responsible for constructing deterministic, immutable, provider-independent PromptRequest packages
from InvestigationReportContext objects. Implements SHA-256 prompt fingerprinting, template registry resolution,
prompt metrics, output contract validation, and multi-versioning.
"""

from __future__ import annotations

import hashlib
import json
from loguru import logger

from app.core.config import Settings, settings
from app.prompts.templates import (
    PromptTemplate,
    PromptTemplateRegistry,
    prompt_template_registry,
)
from app.schemas.investigation_report_context import InvestigationReportContext
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


class PromptBuilder:
    """
    Service responsible for building immutable, fingerprint-hashed PromptRequest objects
    instructing LLMs to format professional investigation reports.
    """

    def __init__(
        self,
        registry: PromptTemplateRegistry | None = None,
        template: PromptTemplate | None = None,
        settings: Settings | None = None,
    ) -> None:
        """
        Initialize PromptBuilder with dependency injection.

        Args:
            registry: Optional PromptTemplateRegistry instance.
            template: Optional explicit PromptTemplate instance.
            settings: Optional application Settings instance.
        """
        self._registry = registry or prompt_template_registry
        self._explicit_template = template
        self._settings = settings

    def build_prompt_request(
        self,
        report_context: InvestigationReportContext,
        template_id: str = "EXECUTIVE_INVESTIGATION_REPORT",
        template_version: str = "1.0",
        model_name: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> PromptRequest:
        """
        Construct a deterministic, fingerprint-hashed PromptRequest package.

        Args:
            report_context: Source canonical InvestigationReportContext DTO.
            template_id: Template identifier in registry (e.g. EXECUTIVE_INVESTIGATION_REPORT).
            template_version: Version of the prompt template.
            model_name: Target LLM model name (defaults to configured GEMINI_MODEL).
            temperature: LLM generation temperature constraint.
            max_tokens: LLM max tokens constraint.

        Returns:
            Immutable PromptRequest object ready for LLM consumption.
        """
        logger.info(
            "Building PromptRequest for target '{}' using template_id '{}' (v{}).",
            report_context.overview.target_value,
            template_id,
            template_version,
        )

        # 1. Resolve Template from Registry or explicit override
        if self._explicit_template:
            template = self._explicit_template
        else:
            template = self._registry.get(template_id)

        # 2. Build Typed Prompt Sections
        system_prompt = template.build_system_prompt()
        developer_instructions = template.build_developer_instructions()

        # 3. Deterministic JSON Context Serialization
        context_dict = report_context.model_dump(mode="json")
        json_data = json.dumps(context_dict, indent=2, sort_keys=True)
        size_bytes = len(json_data.encode("utf-8"))
        serialized_context = SerializedContext(json_data=json_data, size_bytes=size_bytes)

        # 4. Expected Report Structure
        expected_structure = template.expected_structure
        output_requirements = template.output_requirements

        # 5. Compute Prompt Metrics & Diagnostics
        metrics = self._compute_metrics(
            report_context=report_context,
            serialized_context_bytes=size_bytes,
            system_prompt=system_prompt,
            developer_instructions=developer_instructions,
            expected_structure=expected_structure,
        )

        # 6. Generation Constraints
        constraints = PromptConstraints(
            temperature=temperature,
            max_tokens=max_tokens,
            prohibit_speculation=True,
            enforce_provenance_citations=True,
        )

        # 7. Compute Deterministic SHA-256 Prompt Hash
        prompt_hash = self._compute_fingerprint(
            system_prompt=system_prompt,
            developer_instructions=developer_instructions,
            json_data=json_data,
            expected_structure=expected_structure,
        )

        # 8. Metadata
        if model_name is not None and model_name.strip():
            target_model = model_name.strip()
        elif self._settings is not None and self._settings.GEMINI_MODEL:
            target_model = self._settings.GEMINI_MODEL
        else:
            target_model = settings.GEMINI_MODEL

        metadata = PromptMetadata(
            prompt_version="1.0",
            template_version=template.template_version,
            report_context_version=report_context.metadata.report_context_version,
            summary_version=report_context.metadata.generated_from_summary_version,
            template_id=template.template_id,
            model_name=target_model,
            prompt_hash=prompt_hash,
            metrics=metrics,
        )

        prompt_request = PromptRequest(
            metadata=metadata,
            system_prompt=system_prompt,
            developer_instructions=developer_instructions,
            context=serialized_context,
            expected_structure=expected_structure,
            output_requirements=output_requirements,
            constraints=constraints,
        )

        # 9. Perform Validation
        self.validate_prompt_request(prompt_request)

        logger.info(
            "Successfully assembled PromptRequest for target '{}': hash={} length={} bytes.",
            report_context.overview.target_value,
            prompt_hash[:12],
            len(prompt_request.full_prompt),
        )

        return prompt_request

    async def build_prompt_request_async(
        self,
        report_context: InvestigationReportContext,
        template_id: str = "EXECUTIVE_INVESTIGATION_REPORT",
        template_version: str = "1.0",
        model_name: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> PromptRequest:
        """Async wrapper for build_prompt_request."""
        return self.build_prompt_request(
            report_context=report_context,
            template_id=template_id,
            template_version=template_version,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def validate_prompt_request(self, request: PromptRequest) -> None:
        """
        Perform deterministic validation of constructed PromptRequest.
        Raises ValueError if validation fails.
        """
        if not request.context.json_data or request.context.json_data.strip() in ("", "{}"):
            raise ValueError("Prompt validation failed: serialized_context is empty.")

        if not request.system_prompt.operating_rules:
            raise ValueError("Prompt validation failed: operating_rules are missing.")

        if not request.developer_instructions.citation_instructions:
            raise ValueError("Prompt validation failed: citation_instructions are missing.")

        if not request.expected_structure.sections:
            raise ValueError("Prompt validation failed: expected_structure sections are empty.")

        if not request.expected_structure.expected_schema.json_skeleton:
            raise ValueError("Prompt validation failed: expected_schema json_skeleton is empty.")

        if not request.developer_instructions.output_formatting_rules:
            raise ValueError("Prompt validation failed: output_formatting_rules are missing.")

        if not request.metadata.prompt_hash:
            raise ValueError("Prompt validation failed: prompt_hash is missing.")

    def _compute_fingerprint(
        self,
        system_prompt: SystemPrompt,
        developer_instructions: DeveloperInstructions,
        json_data: str,
        expected_structure: ExpectedReportStructure,
    ) -> str:
        """Compute SHA-256 hash digest over prompt components."""
        payload_parts = [
            system_prompt.render(),
            developer_instructions.render(),
            json_data,
            json.dumps([s.model_dump() for s in expected_structure.sections], sort_keys=True),
        ]
        combined = "\n===\n".join(payload_parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _compute_metrics(
        self,
        report_context: InvestigationReportContext,
        serialized_context_bytes: int,
        system_prompt: SystemPrompt,
        developer_instructions: DeveloperInstructions,
        expected_structure: ExpectedReportStructure,
    ) -> PromptMetrics:
        """Compute prompt token estimates and compression metrics."""
        approx_prompt_len = (
            len(system_prompt.render())
            + len(developer_instructions.render())
            + serialized_context_bytes
            + sum(len(s.description) for s in expected_structure.sections)
        )
        estimated_token_count = max(1, approx_prompt_len // 4)

        finding_count = len(report_context.critical_findings)
        entity_count = len(report_context.entity_highlights.highlights)
        timeline_event_count = len(report_context.timeline_highlights.highlights)
        evidence_count = len(report_context.supporting_evidence)

        # Context reduction ratio estimation
        reduction_ratio = round(serialized_context_bytes / max(1, serialized_context_bytes + 2000), 2)

        return PromptMetrics(
            estimated_token_count=estimated_token_count,
            serialized_context_size_bytes=serialized_context_bytes,
            finding_count=finding_count,
            entity_count=entity_count,
            timeline_event_count=timeline_event_count,
            evidence_count=evidence_count,
            context_reduction_ratio=reduction_ratio,
        )

    def build(self, evidence: any) -> str:
        """Legacy backward compatibility method for Sprint 8 callers."""
        logger.warning("Legacy build() called on PromptBuilder. Recommend upgrading to build_prompt_request().")
        if isinstance(evidence, str):
            return evidence
        if hasattr(evidence, "model_dump_json"):
            return evidence.model_dump_json(indent=2)
        return str(evidence)
