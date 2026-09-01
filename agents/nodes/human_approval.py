"""Human approval node for the LangGraph workflow."""
from agents.state import AgentState
from config.logging import logger


class HumanApprovalNode:
    """Pause on first visit and continue only after explicit approval."""

    def __init__(self):
        logger.info("HumanApprovalNode initialized")

    def __call__(self, state: AgentState) -> AgentState:
        emails = state.get("generated_emails", [])
        if not emails:
            state["awaiting_approval"] = False
            state["approved_indices"] = []
            return state

        # Do not use get() here: an empty list is a legitimate explicit
        # decision to approve none. Missing key means first visit.
        if "approved_indices" not in state:
            logger.info("HumanApprovalNode: pausing for human approval")
            state["awaiting_approval"] = True
            return state

        approved = state.get("approved_indices", [])
        logger.info("HumanApprovalNode: approvals received for %s", approved)
        state["awaiting_approval"] = False
        for index, email in enumerate(state.get("generated_emails", [])):
            if isinstance(email, dict):
                email["approved"] = index in approved
            else:
                email.approved = index in approved
        return state
