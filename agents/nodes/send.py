"""Send Node"""

from agents.state import AgentState
from agents.sender import EmailSender
from models.schemas import GeneratedEmail
from config.logging import logger
from services.vectorstore import VectorStoreService

vector_store = VectorStoreService()

class SendNode:
    """
    Sends all approved emails.

    Responsibilities:
    - Validate approved emails
    - Send emails
    - Track successes/failures
    - Store analytics
    """

    def __init__(self):
        self.sender = EmailSender()
        logger.info("SendNode initialized")

    def __call__(self, state: AgentState) -> AgentState:

        logger.info("========== SendNode Started ==========")

        emails = state.get("generated_emails", [])
        approved_indices = state.get("approved_indices", [])

        profile = state.get("user_profile")

        resume_path = None

        if isinstance(profile, dict):
            resume_path = profile.get("resume_path")

        elif profile:
            resume_path = getattr(profile, "resume_path", None)

        # -----------------------------------------
        # Validation
        # -----------------------------------------

        if not emails:

            logger.warning("No generated emails available.")

            state["send_results"] = {
                "sent": 0,
                "failed": 0,
                "skipped": 0,
                "details": [],
            }

            return state

        if approved_indices is None:

            logger.warning("Workflow resumed without approval.")

            state["send_results"] = {
                "sent": 0,
                "failed": 0,
                "skipped": len(emails),
                "details": [],
            }

            return state

        if len(approved_indices) == 0:

            logger.info("No emails approved for sending.")

            state["send_results"] = {
                "sent": 0,
                "failed": 0,
                "skipped": len(emails),
                "details": [],
            }

            return state

        # -----------------------------------------
        # Send Emails
        # -----------------------------------------

        results = {
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        for index in approved_indices:

            if index < 0 or index >= len(emails):

                logger.warning(
                    "Invalid approved index: %d",
                    index,
                )

                results["failed"] += 1

                results["details"].append(
                    {
                        "success": False,
                        "index": index,
                        "error": "Invalid email index",
                    }
                )

                continue

            try:

                email = emails[index]

                if isinstance(email, dict):
                    email = GeneratedEmail(**email)

                send_result = self.sender.send(
                    email,
                    resume_path=resume_path,
                )

                send_result["index"] = index

                results["details"].append(send_result)

                if send_result.get("success"):

                    results["sent"] += 1

                    logger.info(
                        "Email sent to %s",
                        email.recipient_email,
                    )

                    # Store successful email in ChromaDB
                    try:
                        vector_store.add_email(
                            email_id=f"{email.company_name}_{email.recipient_email}",
                            email_data=email.model_dump()
                            if hasattr(email, "model_dump")
                            else email,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to store email in ChromaDB: %s",
                            e,
                        )

                else:

                    results["failed"] += 1

                    logger.warning(
                        "Failed sending email to %s",
                        email.recipient_email,
                    )

            except Exception as e:

                logger.exception(
                    "Unexpected send error."
                )

                results["failed"] += 1

                results["details"].append(
                    {
                        "success": False,
                        "index": index,
                        "error": str(e),
                    }
                )

        results["skipped"] = (
            len(emails) - len(approved_indices)
        )

        # -----------------------------------------
        # Analytics
        # -----------------------------------------

        state["send_results"] = results

        state["send_stats"] = {
            "total_emails": len(emails),
            "approved": len(approved_indices),
            "sent": results["sent"],
            "failed": results["failed"],
            "skipped": results["skipped"],
            "success_rate": round(
                (
                    results["sent"]
                    / max(len(approved_indices), 1)
                )
                * 100,
                2,
            ),
        }

        state["emails_sent"] = (
            results["sent"] > 0
        )

        logger.info(
            "SendNode completed | Sent=%d | Failed=%d | Success Rate=%.2f%%",
            results["sent"],
            results["failed"],
            state["send_stats"]["success_rate"],
        )

        return state