"""Company Research Agent for ColdMail AI"""
from typing import Dict, Any, List
from config.logging import logger


# Common personal email domains
PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.in",
    "hotmail.com", "outlook.com", "live.com", "icloud.com",
    "me.com", "mac.com", "protonmail.com", "zoho.com",
    "aol.com", "mail.com", "yandex.com", "qq.com",
    "163.com", "126.com", "foxmail.com",
}


class CompanyResearcher:
    """Research a company or individual from email."""
    
    def __init__(self):
        pass
    
    def _extract_name_from_email(self, email: str) -> str:
        """Try to extract a person's name from email prefix."""
        prefix = email.split("@")[0]
        # Remove numbers and dots, split by common separators
        import re
        cleaned = re.sub(r'[0-9._\-]+', ' ', prefix).strip()
        words = [w.capitalize() for w in cleaned.split() if len(w) > 1]
        return " ".join(words) if words else prefix.capitalize()
    
    def research(self, email: str) -> Dict[str, Any]:
        """Research from an email address."""
        logger.info(f"Researching {email}...")
        
        if "@" not in email:
            return {
                "name": email.capitalize(),
                "domain": email,
                "description": None,
                "tech_stack": [],
                "is_personal_email": False,
                "role": None,
            }
        
        domain = email.split("@")[1].lower()
        
        # Check if personal email
        if domain in PERSONAL_DOMAINS:
            person_name = self._extract_name_from_email(email)
            return {
                "name": person_name,
                "domain": domain,
                "description": f"Personal contact: {person_name}",
                "tech_stack": [],
                "is_personal_email": True,
                "role": None,
            }
        
        # Company email — derive company name from domain
        name_part = domain.replace(".com", "").replace(".co", "").replace(".in", "").replace(".org", "").replace(".ai", "").replace(".net", "")
        company_name = name_part.split(".")[-1].capitalize()
        
        # Better company name formatting (e.g., evolvexinnovations → Evolvex Innovations)
        import re
        company_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', company_name)
        
        return {
            "name": company_name,
            "domain": domain,
            "description": f"{company_name} is a company we are reaching out to.",
            "tech_stack": [],
            "is_personal_email": False,
            "role": None,
        }
    
    def research_batch(self, emails: List[str]) -> List[Dict[str, Any]]:
        return [self.research(e) for e in emails]