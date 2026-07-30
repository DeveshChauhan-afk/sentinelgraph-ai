"""
Prompt Regression & Determinism Tests (Sprint 9.5 Phase 9.5.5).
"""

from __future__ import annotations

import pytest

from app.evaluation.golden_dataset import get_golden_scenarios
from app.services.prompt_builder import PromptBuilder
from app.services.report_context_builder import ReportContextBuilder


def test_prompt_regression_reproducibility():
    """
    Verify identical InvestigationSummary produces byte-identical PromptRequest and SHA-256 hash.
    """
    scenarios = get_golden_scenarios()
    summary = scenarios["SIMPLE_FRAUD_CASE"].summary

    context_builder = ReportContextBuilder()
    prompt_builder = PromptBuilder()

    context1 = context_builder.build_report_context(summary)
    req1 = prompt_builder.build_prompt_request(context1)

    context2 = context_builder.build_report_context(summary)
    req2 = prompt_builder.build_prompt_request(context2)

    assert req1.metadata.prompt_hash == req2.metadata.prompt_hash
    assert req1.full_prompt == req2.full_prompt
    assert req1.context.json_data == req2.context.json_data
