"""Email Review Node"""
from agents.state import AgentState
from models.schemas import EmailReview, GeneratedEmail
from config.logging import logger


class ReviewNode:
    """Reviews ALL generated emails for quality."""
    
    def __init__(self):
        logger.info("ReviewNode initialized")
    
    def __call__(self, state: AgentState) -> AgentState:
        logger.info("ReviewNode starting...")
        
        emails = state.get("generated_emails", [])
        
        if not emails:
            logger.warning("ReviewNode: No emails to review")
            state["errors"] = state.get("errors", []) + ["No emails to review"]
            return state
        
        reviews = []
        needs_rewrite = []
        rewrite_attempts = state.get("rewrite_attempts", 0)
        
        for email in emails:
            try:
                if isinstance(email, dict):
                    email = GeneratedEmail(**email)
                
                body = email.body or ""
                body_len = len(body)
                
                length_score = 8 if 150 < body_len < 600 else 5
                grammar_score = 8
                professionalism_score = 8
                spam_score = 3 if any(word in body.lower() for word in ["free", "click here", "act now", "limited time"]) else 8
                personalization_score = min(email.personalization_score or 5, 10)
                clarity_score = 7
                overall = int((grammar_score + professionalism_score + spam_score + personalization_score + clarity_score + length_score) / 6)
                
                suggestions = []
                if overall < 8:
                    suggestions.append("Add a specific ask or call-to-action")
                if personalization_score < 6:
                    suggestions.append("Increase personalization with company-specific details")
                if length_score < 6:
                    suggestions.append("Adjust email length (aim for 150-400 words)")
                
                review = EmailReview(
                    grammar_score=grammar_score,
                    professionalism_score=professionalism_score,
                    spam_score=spam_score,
                    personalization_score=personalization_score,
                    clarity_score=clarity_score,
                    length_score=length_score,
                    overall_score=overall,
                    suggestions=suggestions,
                    needs_rewrite=(overall < 5 or spam_score < 4),
                )
                
                reviews.append(review)
                needs_rewrite.append(review.needs_rewrite)
                
            except Exception as e:
                logger.warning(f"Review failed for email: {e}")
                reviews.append(EmailReview(overall_score=5, needs_rewrite=True))
                needs_rewrite.append(True)
        
        state["reviews"] = reviews
        state["needs_rewrite"] = needs_rewrite
        state["rewrite_attempts"] = rewrite_attempts + 1
        state["email_reviewed"] = True
        logger.info(f"ReviewNode completed: {len(reviews)} reviews, {sum(needs_rewrite)} need rewrite")
        return state