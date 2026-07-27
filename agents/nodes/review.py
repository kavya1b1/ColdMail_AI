"""Email Review Node"""

from agents.state import AgentState
from models.schemas import EmailReview, GeneratedEmail
from config.logging import logger


class ReviewNode:
    """
    Reviews generated emails before human approval.

    This node performs lightweight quality checks without calling an LLM.
    """

    SPAM_WORDS = {
        "free",
        "click here",
        "limited time",
        "act now",
        "buy now",
        "guaranteed",
        "exclusive offer",
        "urgent",
    }

    CTA_PHRASES = {
        "looking forward",
        "would love",
        "happy to discuss",
        "thank you",
        "opportunity",
        "interview",
        "conversation",
    }

    def __init__(self):
        logger.info("ReviewNode initialized")

    def __call__(self, state: AgentState) -> AgentState:

        logger.info("========== ReviewNode Started ==========")

        emails = state.get("generated_emails", [])

        if not emails:
            logger.warning("No generated emails found.")
            state.setdefault("errors", []).append(
                "No emails available for review."
            )
            return state

        reviews = []
        rewrite_flags = []

        rewrite_attempts = state.get("rewrite_attempts", 0)

        total_score = 0

        for email in emails:

            try:

                if isinstance(email, dict):
                    email = GeneratedEmail(**email)

                review = self._review_email(email)

                reviews.append(review)
                rewrite_flags.append(review.needs_rewrite)

                total_score += review.overall_score

            except Exception:

                logger.exception("Failed reviewing email")

                reviews.append(
                    EmailReview(
                        grammar_score=5,
                        professionalism_score=5,
                        spam_score=5,
                        personalization_score=5,
                        clarity_score=5,
                        length_score=5,
                        overall_score=5,
                        suggestions=[
                            "Unable to review email."
                        ],
                        needs_rewrite=True,
                    )
                )

                rewrite_flags.append(True)

        average_score = (
            round(total_score / len(reviews), 2)
            if reviews
            else 0
        )

        state["reviews"] = reviews
        state["needs_rewrite"] = rewrite_flags
        state["rewrite_attempts"] = rewrite_attempts + 1
        state["email_reviewed"] = True

        state["review_stats"] = {
            "emails_reviewed": len(reviews),
            "emails_needing_rewrite": sum(rewrite_flags),
            "average_score": average_score,
        }

        logger.info(
            "Review completed | Emails=%d | Rewrite=%d | Avg=%.2f",
            len(reviews),
            sum(rewrite_flags),
            average_score,
        )

        return state

    def _review_email(self, email: GeneratedEmail) -> EmailReview:

        body = (email.body or "").strip()
        subject = (email.subject or "").strip()

        body_lower = body.lower()

        body_length = len(body)

        suggestions = []

        # -----------------------
        # Length
        # -----------------------

        if 200 <= body_length <= 900:
            length_score = 9
        elif 120 <= body_length <= 1200:
            length_score = 7
        else:
            length_score = 5
            suggestions.append(
                "Adjust email length for better readability."
            )

        # -----------------------
        # Grammar
        # -----------------------

        grammar_score = 9

        if body.count("..") > 0:
            grammar_score -= 1

        if body.count("  ") > 2:
            grammar_score -= 1

        # -----------------------
        # Professionalism
        # -----------------------

        professionalism_score = 9

        if body.isupper():
            professionalism_score = 3
            suggestions.append(
                "Avoid excessive capitalisation."
            )

        # -----------------------
        # Spam
        # -----------------------

        spam_hits = sum(
            1
            for word in self.SPAM_WORDS
            if word in body_lower
        )

        spam_score = max(10 - (spam_hits * 2), 2)

        if spam_hits:
            suggestions.append(
                "Reduce promotional wording."
            )

        # -----------------------
        # Personalisation
        # -----------------------

        personalization_score = min(
            email.personalization_score or 5,
            10,
        )

        if personalization_score < 6:
            suggestions.append(
                "Include more company-specific information."
            )

        # -----------------------
        # Clarity
        # -----------------------

        clarity_score = 9

        if not subject:
            clarity_score -= 2
            suggestions.append(
                "Add a meaningful subject line."
            )

        if "dear" not in body_lower and "hi" not in body_lower:
            clarity_score -= 1

        # -----------------------
        # CTA
        # -----------------------

        has_cta = any(
            phrase in body_lower
            for phrase in self.CTA_PHRASES
        )

        if not has_cta:
            clarity_score -= 2

            suggestions.append(
                "End with a stronger call-to-action."
            )

        # -----------------------
        # Overall
        # -----------------------

        overall = round(
            (
                grammar_score
                + professionalism_score
                + spam_score
                + personalization_score
                + clarity_score
                + length_score
            )
            / 6,
            1,
        )

        needs_rewrite = (
            overall < 6
            or spam_score < 5
        )

        return EmailReview(
            grammar_score=grammar_score,
            professionalism_score=professionalism_score,
            spam_score=spam_score,
            personalization_score=personalization_score,
            clarity_score=clarity_score,
            length_score=length_score,
            overall_score=overall,
            suggestions=suggestions,
            needs_rewrite=needs_rewrite,
        )
    

