"""
LangGraph Personalization Node

Generates a personalization strategy before the email
is written.
"""

from config.logging import logger
from agents.personalization import PersonalizationAgent


class PersonalizationNode:
    """Creates a personalization plan for the Writer."""

    def __init__(self):
        self.agent = PersonalizationAgent()

    def __call__(self, state: dict) -> dict:

        logger.info("Starting Personalization Node")

        profile = state.get("user_profile")
        companies = state.get("companies", [])
        jobs = state.get("parsed_jobs", [])
        matches = state.get("matches", [])
        rag_context = state.get("rag_context", "")
        rag_context = state.get("rag_context", "")

        if not profile:
            logger.warning("No profile found.")
            return state

        if not companies:
            logger.warning("No company found.")
            return state

        if not matches:
            logger.warning("No match score found.")
            return state

        company = companies[0]
        job = jobs[0] if jobs else None
        match = matches[0] if matches else None

        try:

            plan = self.agent.generate(
                profile=profile,
                company=company,
                job=job,
                match=match,
                rag_context=rag_context,
            )

            state["personalization_plan"] = plan

            logger.info(
                "Personalization strategy generated successfully."
            )

        except Exception as e:

            logger.exception(
                "Personalization Node failed: %s",
                e,
            )

            state["personalization_plan"] = None

        return state