"""Send Node"""
from agents.state import AgentState
from agents.sender import EmailSender
from models.schemas import GeneratedEmail
from config.logging import logger


class SendNode:
    """Sends ALL approved emails."""
    
    def __init__(self):
        self.sender = EmailSender()
        logger.info("SendNode initialized")
    
    def __call__(self, state: AgentState) -> AgentState:
        logger.info("SendNode starting...")
        
        emails = state.get("generated_emails", [])
        approved_indices = state.get("approved_indices", [])
        
        # Get resume path from profile
        profile = state.get("user_profile")
        resume_path = None
        if isinstance(profile, dict):
            resume_path = profile.get("resume_path")
        elif profile:
            resume_path = getattr(profile, "resume_path", None)
        
        if not emails or not approved_indices:
            logger.warning("SendNode: No approved emails to send")
            state["send_results"] = {"sent": 0, "failed": 0, "details": []}
            return state
        
        results = {"sent": 0, "failed": 0, "details": []}
        
        for idx in approved_indices:
            try:
                if idx < len(emails):
                    email = emails[idx]
                    if isinstance(email, dict):
                        email = GeneratedEmail(**email)
                    
                    result = self.sender.send(email, resume_path=resume_path)
                    if result.get("success"):
                        results["sent"] += 1
                    else:
                        results["failed"] += 1
                    results["details"].append(result)
                    logger.info(f"Processed email to {email.recipient_email} (demo={result.get('demo', False)})")
                    
            except Exception as e:
                logger.warning(f"Send failed for email {idx}: {e}")
                results["failed"] += 1
                results["details"].append({"success": False, "error": str(e)})
        
        state["send_results"] = results
        logger.info(f"SendNode completed: {results['sent']} sent, {results['failed']} failed")
        return state