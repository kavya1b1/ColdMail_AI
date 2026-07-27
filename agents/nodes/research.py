"""Research Agent Node for LangGraph"""
from agents.state import AgentState
from agents.researcher import CompanyResearcher
from models.schemas import CompanyInfo
from config.logging import logger
from services.vectorstore import VectorStoreService
vector_store = VectorStoreService()


class ResearchNode:
    """Research all recipients from emails."""
    
    def __init__(self):
        self.researcher = CompanyResearcher()
        logger.info("ResearchNode initialized")
    
    def __call__(self, state: AgentState) -> AgentState:
        logger.info("ResearchNode starting...")
        emails = state.get("recipient_emails", [])

        resume_text = state.get("resume_text", "")
        resume_skills = state.get("resume_skills", [])

        jd_text = state.get("jd_text", "")
        jd_skills = state.get("jd_skills", [])
        
        if not emails:
            logger.warning("No recipient emails provided")
            state["errors"] = state.get("errors", []) + ["No recipient emails provided"]
            state["companies"] = []
            return state
        
        # RESET: Always start fresh to avoid accumulation from checkpoints
        companies = []
        research_results = []
        
        for email in emails:
            try:
                result = self.researcher.research(email)
                research_results.append(result)
                
                company = CompanyInfo(
                    name=result.get("name", "Contact"),
                    domain=result.get("domain", ""),
                    description=result.get("description"),
                    tech_stack=result.get("tech_stack", []),
                    is_personal_email=result.get("is_personal_email", False),
                    role=result.get("role"),
                )
                companies.append(company)
                try:
                    vector_store.add_company(
                        company_id=company.domain or company.name,
                        company_data=company.model_dump(),
                    )
                except Exception as e:
                    logger.warning(f"Failed to store company in ChromaDB: {e}")
                    
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
        state["research_results"] = research_results
        state["company_researched"] = True
        logger.info(
            "Research completed | Companies: %d | Resume skills: %d | JD skills: %d",
            len(companies),
            len(resume_skills),
            len(jd_skills),
        )
        return state