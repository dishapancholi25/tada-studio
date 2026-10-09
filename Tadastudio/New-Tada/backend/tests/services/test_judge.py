"""Tests for backend.services.evaluation.judge.EvaluationJudge.

Covers the merged-call groundedness support: claim-coverage scoring folded
into the same judge response as the existing quality_score/criteria_scores,
gated by the ``include_groundedness`` flag.
"""

import json

from backend.services.evaluation.judge import EvaluationJudge


class TestParseJudgeResponseGroundedness:
    def test_parses_groundedness_fields_when_included(self):
        raw = json.dumps(
            {
                "quality_score": 88,
                "reasoning": "Mostly accurate.",
                "criteria_scores": {"Faithfulness": 90.0},
                "total_claims": 4,
                "supported_claims": 3,
                "groundedness_score": 0.75,
                "claim_breakdown": [
                    {"claim": "A", "label": "Supported"},
                    {"claim": "B", "label": "Unsupported"},
                ],
                "groundedness_reason": "3 of 4 claims supported.",
            }
        )

        result = EvaluationJudge()._parse_judge_response(raw, include_groundedness=True)

        assert result.total_claims == 4
        assert result.supported_claims == 3
        assert result.groundedness_score == 0.75
        assert result.claim_breakdown == [
            {"claim": "A", "label": "Supported"},
            {"claim": "B", "label": "Unsupported"},
        ]
        assert result.groundedness_reason == "3 of 4 claims supported."

    def test_clamps_and_rounds_groundedness_score(self):
        raw = json.dumps(
            {
                "quality_score": 50,
                "reasoning": "x",
                "criteria_scores": {},
                "groundedness_score": 1.4567,
            }
        )

        result = EvaluationJudge()._parse_judge_response(raw, include_groundedness=True)

        assert result.groundedness_score == 1.0

    def test_drops_claim_entries_with_invalid_or_missing_labels(self):
        raw = json.dumps(
            {
                "quality_score": 50,
                "reasoning": "x",
                "criteria_scores": {},
                "claim_breakdown": [
                    {"claim": "A", "label": "Supported"},
                    {"claim": "B", "label": "Maybe"},
                    {"claim": "C"},
                ],
            }
        )

        result = EvaluationJudge()._parse_judge_response(raw, include_groundedness=True)

        assert result.claim_breakdown == [{"claim": "A", "label": "Supported"}]

    def test_omits_groundedness_fields_when_not_included(self):
        raw = json.dumps(
            {
                "quality_score": 50,
                "reasoning": "x",
                "criteria_scores": {},
                "total_claims": 4,
                "groundedness_score": 0.9,
            }
        )

        result = EvaluationJudge()._parse_judge_response(raw, include_groundedness=False)

        assert result.total_claims is None
        assert result.groundedness_score is None
        assert result.claim_breakdown == []

    def test_parse_failure_leaves_groundedness_fields_at_defaults(self):
        result = EvaluationJudge()._parse_judge_response(
            "not json", include_groundedness=True
        )

        assert result.quality_score == 50.0
        assert result.reasoning.startswith("Failed to parse judge response:")
        assert result.total_claims is None
        assert result.groundedness_score is None
        assert result.claim_breakdown == []


class TestBuildSystemPromptGroundedness:
    def test_includes_groundedness_section_and_schema_when_requested(self):
        prompt = EvaluationJudge()._build_system_prompt(
            has_expected_output=False, include_groundedness=True
        )

        assert "GROUNDEDNESS" in prompt
        assert "groundedness_score = supported_claims / total_claims" in prompt
        assert '"claim_breakdown"' in prompt

    def test_omits_groundedness_section_by_default(self):
        prompt = EvaluationJudge()._build_system_prompt(has_expected_output=False)

        assert "GROUNDEDNESS" not in prompt
        assert '"claim_breakdown"' not in prompt
