"""
Reusable Prompt Templates & Template Registry for SentinelGraph AI (Sprint 9 Phase 4.1 Hotfix).

Defines versioned, reusable, provider-independent prompt template specifications with strict
JSON output contracts and ExpectedReportSchema skeleton definitions.
"""

from __future__ import annotations

import json
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.prompt import (
    DeveloperInstructions,
    ExpectedReportSchema,
    ExpectedReportSection,
    ExpectedReportStructure,
    SystemPrompt,
)

CANONICAL_REPORT_JSON_SKELETON = """{
  "report_id": "RPT-SAMPLE123",
  "target_value": "+919876543210",
  "executive_summary": {
    "summary_text": "High-level overview narrative...",
    "overall_risk_level": "HIGH",
    "key_takeaways": [
      "Key takeaway bullet point 1",
      "Key takeaway bullet point 2"
    ]
  },
  "investigation_scope": {
    "target_value": "+919876543210",
    "target_type": "phone",
    "total_complaints": 2,
    "total_entities": 3,
    "duration_days": 4
  },
  "timeline_summary": {
    "timeline_narrative": "Chronological narrative of key milestones...",
    "milestones": [
      {
        "event_type": "COMPLAINT_CREATED",
        "timestamp": "2026-01-01T10:00:00Z",
        "title": "First Complaint Registered",
        "description": "Complaint C-101 registered against target."
      }
    ]
  },
  "key_findings": [
    {
      "finding_id": "FINDING-EVD-001",
      "title": "High Entity Reuse Across Complaints",
      "description": "Phone number reused across 2 distinct complaints.",
      "severity": "HIGH",
      "confidence": 0.85,
      "citations": [
        "[Complaint: C-101]",
        "[Evidence: EVD-001]"
      ]
    }
  ],
  "fraud_network_evolution": {
    "evolution_narrative": "Network evolution details...",
    "network_stage": "EXPANDING_FRAUD_NETWORK"
  },
  "evidence_assessment": {
    "evidence_summary": "Evidence assessment summary...",
    "supporting_evidence_count": 2
  },
  "recommendations": [
    {
      "recommendation_id": "REC-001",
      "action": "Freeze Payment Identifier 'scammer@upi'",
      "priority": "HIGH",
      "rationale": "Payment identifier reused across 2 complaints.",
      "trigger": "ENTITY_REUSE",
      "target_entities": [
        "+919876543210"
      ]
    }
  ],
  "limitations": {
    "data_quality_assessment": "HIGH",
    "limitations": [
      "Data quality assessment statement."
    ]
  },
  "conclusion": {
    "summary_conclusion": "Concluding summary of findings."
  }
}"""


class PromptTemplate(BaseModel):
    """
    Reusable provider-independent template specifying system role, operating rules,
    output contract, citation guidelines, and style guidelines.
    """

    model_config = ConfigDict(frozen=True)

    template_id: str = Field(
        default="EXECUTIVE_INVESTIGATION_REPORT",
        description="Unique template identifier.",
    )
    template_version: str = Field(
        default="1.0",
        description="Version of this prompt template.",
    )
    ai_role: str = Field(
        ...,
        description="Provider-agnostic LLM system role specification.",
    )
    operating_rules: tuple[str, ...] = Field(
        ...,
        description="Strict operating and reasoning rules.",
    )
    expected_structure: ExpectedReportStructure = Field(
        ...,
        description="Structured output contract defining expected report sections.",
    )
    citation_guidelines: tuple[str, ...] = Field(
        ...,
        description="Provenance citation instructions.",
    )
    style_guidelines: tuple[str, ...] = Field(
        ...,
        description="Tone and formatting guidelines.",
    )
    output_formatting_rules: tuple[str, ...] = Field(
        ...,
        description="Strict JSON formatting rules prohibiting markdown.",
    )
    handling_uncertainty: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Rules for handling low data quality or missing evidence.",
    )

    @property
    def output_requirements(self) -> tuple[str, ...]:
        """Generate output requirements tuple from expected structure."""
        return tuple(
            f"[{s.section_id}] {s.title}: {s.description}"
            for s in self.expected_structure.sections
        )

    def build_system_prompt(self) -> SystemPrompt:
        """Construct typed SystemPrompt model."""
        return SystemPrompt(
            role=self.ai_role,
            operating_rules=self.operating_rules,
        )

    def build_developer_instructions(self) -> DeveloperInstructions:
        """Construct typed DeveloperInstructions model."""
        return DeveloperInstructions(
            citation_instructions=self.citation_guidelines,
            style_guidelines=self.style_guidelines,
            output_formatting_rules=self.output_formatting_rules,
            handling_uncertainty=self.handling_uncertainty,
        )

    def render_system_prompt(self) -> str:
        """Render the system prompt string."""
        return self.build_system_prompt().render()

    def render_developer_instructions(self) -> str:
        """Render developer instructions and citation guidelines."""
        return self.build_developer_instructions().render()


# -----------------------------------------------------------------------------
# Factory Functions for Standard Templates
# -----------------------------------------------------------------------------

def get_executive_report_template(version: str = "1.0") -> PromptTemplate:
    """Executive Investigation Report Template."""
    expected_schema = ExpectedReportSchema(
        json_skeleton=CANONICAL_REPORT_JSON_SKELETON,
        required_field_names=(
            "report_id",
            "target_value",
            "executive_summary",
            "investigation_scope",
            "timeline_summary",
            "key_findings",
            "fraud_network_evolution",
            "evidence_assessment",
            "recommendations",
            "limitations",
            "conclusion",
        ),
    )

    structure = ExpectedReportStructure(
        sections=(
            ExpectedReportSection(
                section_id="EXECUTIVE_SUMMARY",
                title="Executive Summary",
                description="High-level overview of target, overall risk, scope, and duration.",
            ),
            ExpectedReportSection(
                section_id="INVESTIGATION_SCOPE",
                title="Investigation Scope & Targets",
                description="Primary lookup target, entity classifications, and complaint bounds.",
            ),
            ExpectedReportSection(
                section_id="TIMELINE_SUMMARY",
                title="Timeline Summary & Highlights",
                description="Chronological narrative of key milestones.",
            ),
            ExpectedReportSection(
                section_id="KEY_FINDINGS",
                title="Key Findings & Provenance",
                description="Detailed critical findings with natural citations.",
                required_citations=True,
            ),
            ExpectedReportSection(
                section_id="FRAUD_EVOLUTION",
                title="Fraud Network Evolution",
                description="Analysis of origin, payment expansion, communication channels, and network stage.",
            ),
            ExpectedReportSection(
                section_id="EVIDENCE_ASSESSMENT",
                title="Supporting Evidence Assessment",
                description="Material evidence units categorized by severity and confidence.",
                required_citations=True,
            ),
            ExpectedReportSection(
                section_id="RECOMMENDATIONS",
                title="Actionable Recommendations",
                description="Explainable actions with explicit triggers and target entities.",
                required_citations=True,
            ),
            ExpectedReportSection(
                section_id="CONCLUSION_AND_LIMITATIONS",
                title="Conclusion & Data Quality Limitations",
                description="Summary of findings and explicit data completeness notes.",
            ),
        ),
        expected_schema=expected_schema,
    )

    output_formatting_rules = (
        "Return ONLY valid raw JSON.",
        "Return exactly ONE JSON object.",
        "Do NOT wrap output in markdown code blocks or ```json fences.",
        "Do NOT include explanatory text before or after the JSON.",
        "Do NOT rename any JSON keys (e.g. use 'summary_text', NOT 'overview').",
        "Do NOT omit any required fields present in the supplied CANONICAL JSON SKELETON.",
        "Do NOT add extraneous top-level fields.",
        "Ensure arrays (e.g. key_findings, recommendations, key_takeaways) are JSON arrays, NOT objects.",
        "Ensure objects (e.g. executive_summary, evidence_assessment) are JSON objects, NOT arrays.",
    )

    return PromptTemplate(
        template_id="EXECUTIVE_INVESTIGATION_REPORT",
        template_version=version,
        ai_role=(
            "You are SentinelGraph AI, a professional cybercrime and fraud intelligence report writer. "
            "Your role is strictly to output clean, objective JSON technical investigation reports "
            "summarizing supplied deterministic context. You do NOT perform investigation reasoning. "
            "You do NOT infer facts beyond the evidence provided."
        ),
        operating_rules=(
            "Never invent facts or reference information not present in the supplied InvestigationReportContext.",
            "Never speculate, extrapolate, or estimate probabilities not explicitly present in the data.",
            "If data quality is low or information is missing, explicitly state the limitation in the report.",
            "Preserve exact investigation terminology, complaint IDs, evidence IDs, and entity values.",
            "Maintain an objective, technical tone suitable for law enforcement, fraud analysts, and executive leadership.",
            "Never exaggerate confidence scores or risk levels.",
            "Strictly adhere to supplied deterministic risk assessments and findings.",
        ),
        expected_structure=structure,
        citation_guidelines=(
            "Every key finding and recommendation MUST reference available complaint IDs, evidence IDs, or entity IDs.",
            "Use the supplied citation_map to map findings directly to supporting artifacts.",
            "Format citations naturally within brackets, e.g., [Complaint: C-101], [Evidence: EVD-001], [Entity: +919876543210].",
            "Never fabricate or invent citations.",
        ),
        style_guidelines=(
            "Output facts neutrally without sensationalism.",
            "Keep narrative language precise, professional, and concise.",
        ),
        output_formatting_rules=output_formatting_rules,
        handling_uncertainty=(
            "If data quality is rated LOW or MEDIUM, include an explicit data limitations statement.",
            "Never fill gaps using assumptions.",
        ),
    )


def get_technical_report_template(version: str = "1.0") -> PromptTemplate:
    """Technical Deep-Dive Report Template."""
    exec_template = get_executive_report_template(version=version)
    return PromptTemplate(
        template_id="TECHNICAL_INVESTIGATION_REPORT",
        template_version=version,
        ai_role=exec_template.ai_role + " Focus on technical forensic entity links and timeline mechanics.",
        operating_rules=exec_template.operating_rules,
        expected_structure=exec_template.expected_structure,
        citation_guidelines=exec_template.citation_guidelines,
        style_guidelines=exec_template.style_guidelines,
        output_formatting_rules=exec_template.output_formatting_rules,
        handling_uncertainty=exec_template.handling_uncertainty,
    )


def get_law_enforcement_report_template(version: str = "1.0") -> PromptTemplate:
    """Law Enforcement Evidentiary Report Template."""
    exec_template = get_executive_report_template(version=version)
    return PromptTemplate(
        template_id="LAW_ENFORCEMENT_REPORT",
        template_version=version,
        ai_role=exec_template.ai_role + " Structure output for law enforcement evidentiary submission.",
        operating_rules=exec_template.operating_rules,
        expected_structure=exec_template.expected_structure,
        citation_guidelines=exec_template.citation_guidelines,
        style_guidelines=exec_template.style_guidelines,
        output_formatting_rules=exec_template.output_formatting_rules,
        handling_uncertainty=exec_template.handling_uncertainty,
    )


def get_compliance_report_template(version: str = "1.0") -> PromptTemplate:
    """Compliance & AML Regulatory Report Template."""
    exec_template = get_executive_report_template(version=version)
    return PromptTemplate(
        template_id="COMPLIANCE_REPORT",
        template_version=version,
        ai_role=exec_template.ai_role + " Focus on compliance, SAR filing, and regulatory thresholds.",
        operating_rules=exec_template.operating_rules,
        expected_structure=exec_template.expected_structure,
        citation_guidelines=exec_template.citation_guidelines,
        style_guidelines=exec_template.style_guidelines,
        output_formatting_rules=exec_template.output_formatting_rules,
        handling_uncertainty=exec_template.handling_uncertainty,
    )


def get_executive_brief_template(version: str = "1.0") -> PromptTemplate:
    """Executive Brief Template."""
    exec_template = get_executive_report_template(version=version)
    return PromptTemplate(
        template_id="EXECUTIVE_BRIEF",
        template_version=version,
        ai_role=exec_template.ai_role + " Produce a concise one-page executive brief in JSON.",
        operating_rules=exec_template.operating_rules,
        expected_structure=exec_template.expected_structure,
        citation_guidelines=exec_template.citation_guidelines,
        style_guidelines=exec_template.style_guidelines,
        output_formatting_rules=exec_template.output_formatting_rules,
        handling_uncertainty=exec_template.handling_uncertainty,
    )


# -----------------------------------------------------------------------------
# PromptTemplateRegistry
# -----------------------------------------------------------------------------

class PromptTemplateRegistry:
    """
    Registry managing prompt templates by template_id.
    """

    def __init__(self) -> None:
        self._registry: dict[str, PromptTemplate] = {}
        self.register(get_executive_report_template())
        self.register(get_technical_report_template())
        self.register(get_law_enforcement_report_template())
        self.register(get_compliance_report_template())
        self.register(get_executive_brief_template())

    def register(self, template: PromptTemplate) -> None:
        """Register a PromptTemplate."""
        self._registry[template.template_id] = template

    def get(self, template_id: str) -> PromptTemplate:
        """Retrieve a PromptTemplate by ID. Fallback to default if unknown."""
        if template_id in self._registry:
            return self._registry[template_id]
        return get_executive_report_template()


# Global default registry instance
prompt_template_registry = PromptTemplateRegistry()


def get_default_investigation_report_template(version: str = "1.0") -> PromptTemplate:
    """Backward compatibility helper function."""
    return get_executive_report_template(version=version)
