"""
AI Evaluation Report Generator (Sprint 9.5 Phase 9.5.10).

Assembles deterministic citation verification, hallucination detection, quality scoring,
performance benchmarks, and version metadata into an immutable master AIEvaluationReport.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.benchmarking import PerformanceBenchmarkReport, PerformanceBenchmarker
from app.evaluation.citation_verifier import CitationVerificationResult, CitationVerifier
from app.evaluation.hallucination_detector import HallucinationCheckResult, HallucinationDetector
from app.evaluation.quality_evaluator import ReportQualityAssessment, ReportQualityEvaluator
from app.schemas.investigation_report_context import InvestigationReportContext
from app.schemas.prompt import PromptMetadata, PromptRequest
from app.schemas.report import ProfessionalInvestigationReport


class AIEvaluationReport(BaseModel):
    """
    Canonical master AI Evaluation Report summarizing all evaluation sub-systems.
    """

    model_config = ConfigDict(frozen=True)

    evaluation_id: str = Field(..., description="Unique evaluation report identifier.")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when evaluation report was compiled.",
    )
    overall_status: str = Field(..., description="Overall evaluation status (PASS, WARNING, FAIL).")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall AI report quality score.")
    citation_verification: CitationVerificationResult = Field(..., description="Citation verification results.")
    hallucination_check: HallucinationCheckResult = Field(..., description="Hallucination check results.")
    quality_assessment: ReportQualityAssessment = Field(..., description="Quality assessment details.")
    performance_benchmarks: PerformanceBenchmarkReport = Field(..., description="Performance benchmark timings.")
    prompt_metadata: PromptMetadata = Field(..., description="Prompt metadata and fingerprint.")
    recommendations: tuple[str, ...] = Field(default_factory=tuple, description="Evaluation feedback recommendations.")


class AIEvaluationReportGenerator:
    """
    Orchestration service compiling master AIEvaluationReport objects.
    """

    def evaluate_report(
        self,
        report: ProfessionalInvestigationReport,
        context: InvestigationReportContext,
        prompt_request: PromptRequest,
        summary: any,
        sample_llm_text: str,
    ) -> AIEvaluationReport:
        """
        Run complete deterministic evaluation suite over an investigation report.

        Args:
            report: Target ProfessionalInvestigationReport.
            context: Source InvestigationReportContext.
            prompt_request: PromptRequest sent to LLM.
            summary: Source InvestigationSummary.
            sample_llm_text: Raw completion text string for benchmarking.

        Returns:
            Immutable master AIEvaluationReport.
        """
        eval_id = f"EVAL-{uuid4().hex[:10].upper()}"

        # 1. Citation Verification
        citation_result = CitationVerifier().verify(report=report, context=context)

        # 2. Hallucination Detection
        hallucination_result = HallucinationDetector().detect(report=report, context=context)

        # 3. Quality Assessment
        quality_result = ReportQualityEvaluator().evaluate(report=report, context=context)

        # 4. Performance Benchmarks
        benchmark_result = PerformanceBenchmarker().benchmark_pipeline(
            summary=summary, sample_llm_text=sample_llm_text
        )

        # 5. Determine Overall Status & Recommendations
        recommendations_list = []
        status = "PASS"

        if not citation_result.is_valid:
            status = "WARNING"
            recommendations_list.append(f"Invalid citations detected: {citation_result.invalid_citations}")

        if not hallucination_result.is_clean:
            status = "FAIL" if hallucination_result.status == "UNSUPPORTED_FINDING" else "WARNING"
            recommendations_list.append(f"Hallucination warning: {hallucination_result.status}")

        if quality_result.overall_quality_score < 0.70:
            if status != "FAIL":
                status = "WARNING"
            recommendations_list.append("Report quality score below 0.70 threshold.")

        if not recommendations_list:
            recommendations_list.append("Report passed all deterministic evaluation benchmarks cleanly.")

        return AIEvaluationReport(
            evaluation_id=eval_id,
            overall_status=status,
            quality_score=quality_result.overall_quality_score,
            citation_verification=citation_result,
            hallucination_check=hallucination_result,
            quality_assessment=quality_result,
            performance_benchmarks=benchmark_result,
            prompt_metadata=prompt_request.metadata,
            recommendations=tuple(recommendations_list),
        )
