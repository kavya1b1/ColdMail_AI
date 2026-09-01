"""Evidence-aware email review node."""
import re
from agents.state import AgentState
from models.schemas import EmailReview, GeneratedEmail
from services.llm import LLMService
from config.logging import logger


class ReviewNode:
    """Review generated emails with deterministic checks plus LLM evaluation."""

    def __init__(self):
        self.llm = LLMService()

    def __call__(self, state: AgentState) -> AgentState:
        emails = state.get("generated_emails", [])
        evidence = state.get("research_evidence", [])
        if not emails:
            state["errors"] = state.get("errors", []) + ["No emails to review"]
            return state

        reviews, needs_rewrite = [], []
        attempts = state.get("rewrite_attempts", 0)
        evidence_text = " ".join(e.get("claim", "") for e in evidence).lower()

        for item in emails:
            email = GeneratedEmail(**item) if isinstance(item, dict) else item
            body = email.body or ""
            length = len(body.split())
            spam_terms = ["free", "click here", "act now", "limited time", "guaranteed"]
            spam_hits = sum(1 for term in spam_terms if term in body.lower())
            llm_review = self.llm.review_email(body, evidence) if self.llm.is_available() else None

            if llm_review:
                review = EmailReview(
                    grammar_score=llm_review.grammar_score,
                    professionalism_score=llm_review.professionalism_score,
                    spam_score=max(1, 10 - llm_review.spam_risk),
                    personalization_score=llm_review.personalization_score,
                    clarity_score=llm_review.clarity_score,
                    length_score=8 if 120 <= length <= 220 else 5,
                    overall_score=llm_review.overall_score,
                    suggestions=llm_review.suggestions,
                    needs_rewrite=llm_review.needs_rewrite,
                )
                if llm_review.unsupported_claims:
                    review.suggestions.extend(["Unsupported claim: " + c for c in llm_review.unsupported_claims])
            else:
                length_score = 8 if 120 <= length <= 220 else 5
                spam_score = max(1, 10 - spam_hits * 3)
                personalization = min(10, max(1, round(email.personalization_score / 10)))
                overall = round((8 + 8 + spam_score + personalization + 8 + length_score) / 6)
                review = EmailReview(
                    grammar_score=8, professionalism_score=8, spam_score=spam_score,
                    personalization_score=personalization, clarity_score=8,
                    length_score=length_score, overall_score=overall,
                    suggestions=[] if overall >= 7 else ["Make the email more specific and concise"],
                    needs_rewrite=overall < 7,
                )

            # Hard safety/quality gates independent of the model.
            if not email.recipient_email:
                review.suggestions.append("Recipient email is missing; do not send until verified")
                review.needs_rewrite = True
            if length < 80 or length > 260:
                review.suggestions.append("Target 120-220 words for concise outreach")
                review.needs_rewrite = True
            if not evidence and re.search(r"\b(recent|launched|built|developed|platform|product)\b", body, re.I):
                review.suggestions.append("Company-specific claims require verified evidence")
                review.needs_rewrite = True

            reviews.append(review)
            needs_rewrite.append(review.needs_rewrite)

        state["reviews"] = reviews
        state["needs_rewrite"] = needs_rewrite
        state["rewrite_attempts"] = attempts + 1
        state["email_reviewed"] = True
        logger.info("ReviewNode completed: %d reviews, %d need rewrite", len(reviews), sum(needs_rewrite))
        return state
