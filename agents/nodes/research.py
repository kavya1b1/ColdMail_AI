"""Research Agent Node for LangGraph"""
from agents.state import AgentState
from agents.researcher import CompanyResearcher
from models.schemas import CompanyInfo
from config.logging import logger


class ResearchNode:
    """Research all recipients from emails."""
    
    def __init__(self):
        self.researcher = CompanyResearcher()
        logger.info("ResearchNode initialized")
    
    def __call__(self, state: AgentState) -> AgentState:
        logger.info("ResearchNode starting...")
        emails = state.get("recipient_emails", [])
        
        if not emails:
            logger.warning("No recipient emails provided")
            state["errors"] = state.get("errors", []) + ["No recipient emails provided"]
            state["companies"] = []
            return state
        
        # RESET: Always start fresh to avoid accumulation from checkpoints
        companies = []
        
        for email in emails:
            try:
                result = self.researcher.research(email)
                
                company = CompanyInfo(
                    name=result.get("name", "Contact"),
                    domain=result.get("domain", ""),
                    description=result.get("description"),
                    tech_stack=result.get("tech_stack", []),
                    is_personal_email=result.get("is_personal_email", False),
                    role=result.get("role"),
                )
                companies.append(company)
                logger.info(f"Research succeeded for {email} → {company.name} (personal={company.is_personal_email})")
                
            except Exception as e:
                logger.warning(f"Research failed for {email}: {e}")
                domain = email.split("@")[1] if "@" in email else ""
                companies.append(CompanyInfo(
                    name=email.split("@")[0].capitalize() if "@" in email else email,
                    domain=domain,
                    is_personal_email=False
                ))
        
        state["companies"] = companies
        state["company_researched"] = True
        logger.info(f"ResearchNode completed: {len(companies)} contacts")
        return state