"""LangGraph workflow builder for the ColdMail AI pipeline."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal

from agents.state import AgentState
from agents.nodes.research import ResearchNode
from agents.nodes.parse import ResumeParserNode, JobDescriptionParserNode
from agents.nodes.match import MatchNode
from agents.nodes.write import WriteNode
from agents.nodes.review import ReviewNode
from agents.nodes.human_approval import HumanApprovalNode
from agents.nodes.send import SendNode
from config.logging import logger


class ColdMailWorkflow:
    def __init__(self):
        self.builder = StateGraph(AgentState)
        self._build_graph()
        logger.info("ColdMailWorkflow initialized")

    def _build_graph(self):
        self.builder.add_node("parse_resume", ResumeParserNode())
        self.builder.add_node("parse_jd", JobDescriptionParserNode())
        self.builder.add_node("research", ResearchNode())
        self.builder.add_node("match", MatchNode())
        self.builder.add_node("write", WriteNode())
        self.builder.add_node("review", ReviewNode())
        self.builder.add_node("human_approval", HumanApprovalNode())
        self.builder.add_node("send", SendNode())

        # Parse inputs before research/matching. Parser nodes safely no-op when input is absent.
        self.builder.set_entry_point("parse_resume")
        self.builder.add_edge("parse_resume", "parse_jd")
        self.builder.add_edge("parse_jd", "research")
        self.builder.add_edge("research", "match")
        self.builder.add_edge("match", "write")
        self.builder.add_edge("write", "review")

        self.builder.add_conditional_edges(
            "review", self._after_review,
            {"rewrite": "write", "approve": "human_approval", "end": END}
        )
        self.builder.add_conditional_edges(
            "human_approval", self._after_approval,
            {"send": "send", "pause": END}
        )
        self.builder.add_edge("send", END)
        self.graph = self.builder.compile(checkpointer=MemorySaver())

    def _after_review(self, state: AgentState) -> Literal["rewrite", "approve", "end"]:
        if len(state.get("errors", [])) > 5:
            return "end"
        if any(state.get("needs_rewrite", [])) and state.get("rewrite_attempts", 0) < 3:
            return "rewrite"
        return "approve"

    def _after_approval(self, state: AgentState) -> Literal["send", "pause"]:
        if state.get("awaiting_approval"):
            return "pause"
        return "send" if state.get("approved_indices") else "pause"

    def run(self, initial_state: AgentState, thread_id: str = None):
        config = {"configurable": {"thread_id": thread_id or "default"}}
        for event in self.graph.stream(initial_state, config):
            if "__end__" not in event:
                logger.info("Workflow event: %s", list(event.keys()))
        return self.graph.get_state(config)

    def get_graphviz(self):
        return self.graph.get_graph().draw_mermaid()
