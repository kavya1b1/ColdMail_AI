"""Regression tests for the V3 AI quality layer."""
from models.ai_schemas import GeneratedEmailDraft, ResearchEvidence, ResearchResult, EmailReviewResult


def test_generated_email_schema_rejects_empty_subject():
    try:
        GeneratedEmailDraft(subject="", body="A valid body that is long enough for validation.")
        assert False, "empty subject should fail validation"
    except Exception:
        pass


def test_research_evidence_has_traceable_source():
    evidence = ResearchEvidence(id="x", claim="Company builds AI tools", source_url="https://example.com", confidence=0.9)
    assert evidence.source_url.startswith("https://")
    assert evidence.confidence == 0.9


def test_research_result_defaults_to_no_evidence():
    result = ResearchResult(company_name="Example", domain="example.com", researched_at="2026-01-01T00:00:00Z")
    assert result.evidence == []
    assert result.research_confidence == 0.0


def test_review_schema_has_grounding_and_risk_scores():
    review = EmailReviewResult(
        grammar_score=9, professionalism_score=9, personalization_score=8,
        clarity_score=9, evidence_grounding_score=10, hallucination_risk=1,
        spam_risk=0, overall_score=9
    )
    assert review.evidence_grounding_score == 10
    assert review.hallucination_risk == 1
