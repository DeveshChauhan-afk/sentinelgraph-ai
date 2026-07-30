"""
Schemas for PromptBuilder & Prompt Templates (Sprint 9 Phase 4.1 Hotfix).

Provides strongly typed, provider-independent, immutable prompt models with
deterministic JSON output contracts (ExpectedReportSchema), fingerprinting,
diagnostics, and context compression metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class PromptSection(BaseModel):
    """
    Immutable strongly typed prompt section.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Section title/identifier.")
    content: str = Field(..., description="Section content.")


class SystemPrompt(BaseModel):
    """
    Typed System Role and Operating Rules section.
    """

    model_config = ConfigDict(frozen=True)

    role: str = Field(..., description="Provider-agnostic LLM system role.")
    operating_rules: tuple[str, ...] = Field(..., description="Strict operating rules.")

    def render(self) -> str:
        """Render system role and operating rules string."""
        rules_str = "\n".join(
            f"{idx}. {r}" for idx, r in enumerate(self.operating_rules, start=1)
        )
        return f"{self.role}\n\nOPERATING RULES:\n{rules_str}"


class DeveloperInstructions(BaseModel):
    """
    Typed Developer Instructions, Citation Guidelines, and Style Rules.
    """

    model_config = ConfigDict(frozen=True)

    citation_instructions: tuple[str, ...] = Field(
        ..., description="Provenance citation rules."
    )
    style_guidelines: tuple[str, ...] = Field(
        ..., description="Style and tone rules."
    )
    output_formatting_rules: tuple[str, ...] = Field(
        default_factory=tuple, description="Strict JSON formatting rules prohibiting markdown."
    )
    handling_uncertainty: tuple[str, ...] = Field(
        default_factory=tuple, description="Data quality & uncertainty rules."
    )

    def render(self) -> str:
        """Render developer instructions, citation rules, formatting rules, and style guidelines."""
        citations = "\n".join(f"- {c}" for c in self.citation_instructions)
        styles = "\n".join(f"- {s}" for s in self.style_guidelines)
        formatting = (
            "\n".join(f"- {f}" for f in self.output_formatting_rules)
            if self.output_formatting_rules
            else ""
        )
        uncertainty = (
            "\n".join(f"- {u}" for u in self.handling_uncertainty)
            if self.handling_uncertainty
            else ""
        )
        res = f"CITATION GUIDELINES:\n{citations}\n\nSTYLE GUIDELINES:\n{styles}"
        if formatting:
            res += f"\n\nSTRICT JSON OUTPUT RULES:\n{formatting}"
        if uncertainty:
            res += f"\n\nHANDLING UNCERTAINTY:\n{uncertainty}"
        return res


class SerializedContext(BaseModel):
    """
    Typed serialized investigation report context.
    """

    model_config = ConfigDict(frozen=True)

    json_data: str = Field(
        ..., description="JSON serialized InvestigationReportContext string."
    )
    size_bytes: int = Field(..., description="Byte size of serialized context.")


class ExpectedReportSection(BaseModel):
    """
    Defines a required report section in the structured output contract.
    """

    model_config = ConfigDict(frozen=True)

    section_id: str = Field(..., description="Section identifier.")
    title: str = Field(..., description="Display title.")
    description: str = Field(..., description="Required content description.")
    required_citations: bool = Field(
        default=False, description="Whether citations are required."
    )


class ExpectedReportSchema(BaseModel):
    """
    Deterministic schema specification defining the exact JSON output contract.
    """

    model_config = ConfigDict(frozen=True)

    json_skeleton: str = Field(
        ..., description="Canonical JSON skeleton string with exact field names."
    )
    required_field_names: tuple[str, ...] = Field(
        ..., description="Top-level required field names."
    )


class ExpectedReportStructure(BaseModel):
    """
    Structured output contract defining expected report sections and canonical JSON schema.
    """

    model_config = ConfigDict(frozen=True)

    sections: tuple[ExpectedReportSection, ...] = Field(
        ..., description="Ordered report sections."
    )
    expected_schema: ExpectedReportSchema = Field(
        default_factory=lambda: ExpectedReportSchema(
            json_skeleton='{"report_id": "string", "target_value": "string"}',
            required_field_names=("report_id", "target_value"),
        ),
        description="Deterministic JSON schema skeleton.",
    )


class PromptMetrics(BaseModel):
    """
    Diagnostic metrics capturing token estimates and context compression details.
    """

    model_config = ConfigDict(frozen=True)

    estimated_token_count: int = Field(
        default=0, description="Estimated total prompt token count."
    )
    serialized_context_size_bytes: int = Field(
        default=0, description="Context size in bytes."
    )
    finding_count: int = Field(
        default=0, description="Number of selected findings."
    )
    entity_count: int = Field(
        default=0, description="Number of selected entity highlights."
    )
    timeline_event_count: int = Field(
        default=0, description="Number of selected timeline events."
    )
    evidence_count: int = Field(
        default=0, description="Number of supporting evidence units."
    )
    context_reduction_ratio: float = Field(
        default=0.0, description="Context reduction ratio."
    )


class PromptMetadata(BaseModel):
    """
    Metadata for PromptRequest including explicit multi-versioning and prompt fingerprint.
    """

    model_config = ConfigDict(frozen=True)

    prompt_version: str = Field(
        default="1.0", description="Prompt schema version."
    )
    template_version: str = Field(
        default="1.0", description="Template version."
    )
    report_context_version: str = Field(
        default="1.0", description="Report context version."
    )
    summary_version: str = Field(
        default="1.0", description="Source summary version."
    )
    template_id: str = Field(
        default="EXECUTIVE_INVESTIGATION_REPORT",
        description="Template identifier.",
    )
    model_name: str = Field(
        default="gemini-3.5-flash-lite", description="Target LLM model name."
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when prompt was assembled.",
    )
    prompt_hash: str = Field(
        ..., description="SHA-256 fingerprint hash of prompt payload."
    )
    metrics: PromptMetrics = Field(
        default_factory=PromptMetrics,
        description="Prompt diagnostics and compression metrics.",
    )


class PromptConstraints(BaseModel):
    """
    Provider-agnostic LLM generation constraints.
    """

    model_config = ConfigDict(frozen=True)

    temperature: float = Field(
        default=0.2, ge=0.0, le=2.0, description="Generation temperature."
    )
    max_tokens: int = Field(
        default=4096, ge=1, description="Max token limit."
    )
    prohibit_speculation: bool = Field(
        default=True, description="Strict speculation prohibition."
    )
    enforce_provenance_citations: bool = Field(
        default=True, description="Enforce provenance citations."
    )


class PromptRequest(BaseModel):
    """
    Canonical immutable provider-independent PromptRequest package.
    """

    model_config = ConfigDict(frozen=True)

    metadata: PromptMetadata = Field(
        ..., description="Prompt metadata and fingerprint."
    )
    system_prompt: SystemPrompt = Field(
        ..., description="Typed system prompt."
    )
    developer_instructions: DeveloperInstructions = Field(
        ..., description="Typed developer instructions."
    )
    context: SerializedContext = Field(
        ..., description="Typed serialized context."
    )
    expected_structure: ExpectedReportStructure = Field(
        ..., description="Structured output contract."
    )
    output_requirements: tuple[str, ...] = Field(
        default_factory=tuple, description="Output requirements."
    )
    constraints: PromptConstraints = Field(
        ..., description="Generation constraints."
    )

    @property
    def serialized_context(self) -> str:
        """Backward compatibility helper returning JSON context string."""
        return self.context.json_data

    @property
    def full_prompt(self) -> str:
        """
        Assemble the complete, deterministic combined prompt string.
        """
        sections = [
            "=== LLM SYSTEM ROLE & OPERATING RULES ===",
            self.system_prompt.render(),
            "",
            "=== LLM INSTRUCTIONS & CITATION RULES ===",
            self.developer_instructions.render(),
            "",
            "=== INVESTIGATION REPORT CONTEXT (DETERMINISTIC DATA) ===",
            self.context.json_data,
            "",
            "=== CANONICAL JSON OUTPUT SKELETON (MANDATORY EXACT FIELD NAMES) ===",
            self.expected_structure.expected_schema.json_skeleton,
            "",
            "=== REQUIRED REPORT OUTPUT SECTIONS ===",
            "\n".join(
                f"- [{s.section_id}] {s.title}: {s.description}"
                for s in self.expected_structure.sections
            ),
        ]
        return "\n".join(sections)
