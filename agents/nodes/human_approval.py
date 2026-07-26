"""Human Approval Node"""
from agents.state import AgentState
from config.logging import logger


class HumanApprovalNode:
    """Handles approval for ALL generated emails."""
    
    def __init__(self):
        logger.info("HumanApprovalNode initialized")
    
    def __call__(self, state: AgentState) -> AgentState:
        logger.info("HumanApprovalNode starting...")
        
        emails = state.get("generated_emails", [])
        
        if not emails:
            logger.warning("HumanApprovalNode: 0 emails need approval")
            state["awaiting_approval"] = False
            state["approved_indices"] = []
            return state
        
        # Check if user has already provided approval via UI (second run)
        already_approved = state.get("approved_indices")
        if already_approved is not None:
            # This is a re-run after user approval
            logger.info(f"HumanApprovalNode: Using pre-approved indices: {already_approved}")
            state["awaiting_approval"] = False
            return state
        
        # First run: pause for human approval
        logger.info("HumanApprovalNode: Pausing for human approval")
        state["awaiting_approval"] = True
        state["approved_indices"] = []  # Empty until user approves
        return state