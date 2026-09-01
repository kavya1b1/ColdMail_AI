"""Evidence-backed research node for LangGraph."""
from agents.state import AgentState
from agents.researcher import CompanyResearcher
from models.schemas import CompanyInfo
from config.logging import logger


class ResearchNode:
    """Research recipients and retain source-backed evidence."""

    def __init__(self):
        self.researcher = CompanyResearcher()
        logger.info("ResearchNode initialized")

    def __call__(self, state: AgentState) -> AgentState:
        emails = state.get("recipient_emails", [])
        if not emails:
            state["errors"] = state.get("errors", []) + ["No recipient emails provided"]
            state["companies"] = []
            state["research_evidence"] = []
            return state

        companies, all_evidence = [], []
        for email in emails:
            try:
                result = self.researcher.research(email)
                company = CompanyInfo(
                    name=result.get("name", "Contact"),
                    domain=result.get("domain", ""),
                    description=result.get("description"),
                    tech_stack=result.get("tech_stack", []),
                    careers_page=result.get("careers_page"),
                    is_personal_email=result.get("is_personal_email", False),
                    role=result.get("role"),
                )
                companies.append(company)
                all_evidence.extend(result.get("evidence", []))
                logger.info("Research succeeded for %s -> %s", email, company.name)
            except Exception as exc:
                logger.warning("Research failed for %s: %s", email, exc)
                domain = email.split("@", 1)[1] if "@" in email else ""
                companies.append(CompanyInfo(name=email.split("@")[0].capitalize(), domain=domain, is_personal_email=False))

        state["companies"] = companies
        state["research_evidence"] = all_evidence
        state["company_researched"] = True
        state["researched"] = True
        logger.info("ResearchNode completed: %d companies, %d evidence items", len(companies), len(all_evidence))
        return state
