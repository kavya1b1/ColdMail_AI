"""Email Writer Node"""

from agents.state import AgentState
from agents.writer import EmailWriter
from models.schemas import (
    UserProfile,
)
from config.logging import logger

from services.vectorstore import VectorStoreService

vector_store = VectorStoreService()

class WriteNode:
    """
    Generates personalised cold emails for every researched company.
    Responsible only for orchestration.
    """

    def __init__(self):
        self.writer = EmailWriter()
        logger.info("WriteNode initialized")

    def __call__(self, state: AgentState) -> AgentState:
        logger.info("========== WriteNode Started ==========")

        # -------------------------
        # Load State
        # -------------------------

        profile_data = state.get("user_profile")

        companies = state.get("companies", [])
        matches = state.get("matches", [])
        jobs = state.get("parsed_jobs", [])

        recipient_emails = state.get("recipient_emails", [])
        roles = state.get("roles", [])

        # New context collected by previous nodes
        resume_text = state.get("resume_text", "")
        jd_text = state.get("jd_text", "")

        research_results = state.get("research_results", [])
        match_context = state.get("match_context", [])

        # -------------------------
        # Validation
        # -------------------------

        if profile_data is None:
            logger.error("WriteNode: Missing user profile")
            state.setdefault("errors", []).append("Missing user profile")
            return state

        if not companies:
            logger.error("WriteNode: No companies available")
            state.setdefault("errors", []).append("No companies to write for")
            return state

        if isinstance(profile_data, dict):
            profile = UserProfile(**profile_data)
        else:
            profile = profile_data

        if len(matches) != len(companies):
            logger.warning(
                "Match count (%d) != Company count (%d)",
                len(matches),
                len(companies),
            )

        if len(recipient_emails) != len(companies):
            logger.warning(
                "Recipient count (%d) != Company count (%d)",
                len(recipient_emails),
                len(companies),
            )

        # -------------------------
        # Build Writer Context
        # -------------------------

        rag_context = ""

        try:
            if companies:
                rag_context = vector_store.get_relevant_context(
                    company_name=companies[0].name,
                    skills=profile.skills,
                )
        except Exception as e:
            logger.warning(f"Failed to retrieve RAG context: {e}")

        writer_context = {
            "resume_text": resume_text,
            "jd_text": jd_text,
            "research_results": research_results,
            "match_context": match_context,
            "rag_context": rag_context,
        }

        # -------------------------
        # Generate Emails
        # -------------------------

        try:

            emails = self.writer.write_batch(
                profile=profile,
                companies=companies,
                matches=matches,
                recipient_emails=recipient_emails,
                roles=roles,
                jobs=jobs,
                context=writer_context,   # <-- add this in EmailWriter
            )

            if emails is None:
                emails = []

        except Exception as e:
            logger.exception("Email generation failed")

            state.setdefault("errors", []).append(
                f"Email generation failed: {str(e)}"
            )

            return state

        # -------------------------
        # Save Results
        # -------------------------

        state["generated_emails"] = emails
        state["email_written"] = True

        state["generation_stats"] = {
            "emails_generated": len(emails),
            "companies_processed": len(companies),
            "successful_matches": len(matches),
            "research_items": len(research_results),
        }

        logger.info(
            "WriteNode completed | Emails=%d | Companies=%d",
            len(emails),
            len(companies),
        )

        return state