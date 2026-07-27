"""Human Approval Node"""

from agents.state import AgentState
from config.logging import logger


class HumanApprovalNode:
    """
    Human-in-the-loop approval node.

    Behaviour:

    1. First execution
       -> Pause workflow and wait for UI approval.

    2. Resume execution
       -> Continue using the approval information
          already stored in the state.

    Supports:
    - Partial approval
    - Reject all
    - Future rewrite loops
    """

    def __init__(self):
        logger.info("HumanApprovalNode initialized")

    def __call__(self, state: AgentState) -> AgentState:

        logger.info("========== Human Approval ==========")

        emails = state.get("generated_emails", [])

        if not emails:

            logger.warning("No generated emails found.")

            state["awaiting_approval"] = False
            state["approved_indices"] = []

            state.setdefault("errors", []).append(
                "No emails available for approval."
            )

            return state

        approved_indices = state.get("approved_indices")
        rejected_indices = state.get("rejected_indices", [])

        rewrite_requested = state.get(
            "rewrite_requested",
            False,
        )

        # ------------------------------------
        # Resume after UI action
        # ------------------------------------

        if approved_indices is not None:

            logger.info(
                "Approval received | Approved=%d | Rejected=%d",
                len(approved_indices),
                len(rejected_indices),
            )

            state["awaiting_approval"] = False
            state["human_approved"] = True

            state["approval_stats"] = {
                "total": len(emails),
                "approved": len(approved_indices),
                "rejected": len(rejected_indices),
                "rewrite_requested": rewrite_requested,
            }

            return state

        # ------------------------------------
        # First execution
        # ------------------------------------

        logger.info(
            "Waiting for human approval (%d emails).",
            len(emails),
        )

        state["awaiting_approval"] = True
        state["human_approved"] = False

        # UI will populate these later
        state["approved_indices"] = None
        state["rejected_indices"] = []

        state["approval_stats"] = {
            "total": len(emails),
            "approved": 0,
            "rejected": 0,
            "rewrite_requested": False,
        }

        return state