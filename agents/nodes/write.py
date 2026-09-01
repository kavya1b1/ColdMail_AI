"""Email Writer Node"""
from agents.state import AgentState
from agents.writer import EmailWriter
from models.schemas import UserProfile
from config.logging import logger


class WriteNode:
    """Generate emails using matches and source-backed evidence."""

    def __init__(self):
        self.writer = EmailWriter()

    def __call__(self, state: AgentState) -> AgentState:
        profile_data = state.get("user_profile")
        companies = state.get("companies", [])
        matches = state.get("matches", [])
        if not profile_data or not companies:
            state["errors"] = state.get("errors", []) + ["Missing profile or companies for writing"]
            return state
        profile = UserProfile(**profile_data) if isinstance(profile_data, dict) else profile_data
        state["generated_emails"] = self.writer.write_batch(
            profile=profile,
            companies=companies,
            matches=matches,
            recipient_emails=state.get("recipient_emails", []),
            roles=state.get("roles", []),
            jobs=state.get("parsed_jobs", []),
            evidence=state.get("research_evidence", []),
        )
        state["email_written"] = True
        logger.info("WriteNode completed: %d emails", len(state["generated_emails"]))
        return state
