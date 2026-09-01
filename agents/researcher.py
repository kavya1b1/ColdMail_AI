"""Evidence-backed company research agent."""
from typing import Dict, Any, List
from datetime import datetime, timezone
from urllib.parse import urljoin
import re

import httpx
import trafilatura

from config.logging import logger

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.in", "hotmail.com",
    "outlook.com", "live.com", "icloud.com", "me.com", "mac.com",
    "protonmail.com", "zoho.com", "aol.com", "mail.com", "yandex.com",
    "qq.com", "163.com", "126.com", "foxmail.com",
}


class CompanyResearcher:
    """Research public company pages and preserve source-backed evidence."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def _extract_name_from_email(self, email: str) -> str:
        prefix = email.split("@")[0]
        cleaned = re.sub(r"[0-9._\-]+", " ", prefix).strip()
        words = [w.capitalize() for w in cleaned.split() if len(w) > 1]
        return " ".join(words) if words else prefix.capitalize()

    @staticmethod
    def _company_name(domain: str) -> str:
        labels = domain.split(".")
        name = labels[-2] if len(labels) >= 2 else labels[0]
        return re.sub(r"[-_]+", " ", name).title()

    def _fetch_page(self, url: str) -> tuple[str, str]:
        try:
            response = httpx.get(url, timeout=self.timeout, follow_redirects=True, headers={"User-Agent": "ColdMailAI/3.0"})
            response.raise_for_status()
            text = trafilatura.extract(response.text, include_links=True, include_tables=False) or ""
            return text, str(response.url)
        except Exception as exc:
            logger.info("Research fetch failed for %s: %s", url, exc)
            return "", url

    @staticmethod
    def _extract_tech(text: str) -> List[str]:
        catalog = [
            "python", "javascript", "typescript", "react", "vue", "angular", "node.js",
            "django", "flask", "fastapi", "java", "go", "rust", "aws", "azure", "gcp",
            "docker", "kubernetes", "terraform", "postgresql", "mysql", "mongodb", "redis",
            "machine learning", "deep learning", "tensorflow", "pytorch", "generative ai",
            "llm", "rag", "langchain", "langgraph", "graphql", "microservices",
        ]
        lower = text.lower()
        return [skill.title() if skill != "node.js" else "Node.js" for skill in catalog if skill in lower]

    def research(self, email: str) -> Dict[str, Any]:
        logger.info("Researching %s...", email)
        if "@" not in email:
            return {"name": email.capitalize(), "domain": email, "description": None, "tech_stack": [], "is_personal_email": False, "role": None, "evidence": []}

        domain = email.split("@", 1)[1].lower().strip()
        if domain in PERSONAL_DOMAINS:
            name = self._extract_name_from_email(email)
            return {"name": name, "domain": domain, "description": f"Personal contact: {name}", "tech_stack": [], "is_personal_email": True, "role": None, "evidence": []}

        company_name = self._company_name(domain)
        base = f"https://{domain}/"
        text, final_url = self._fetch_page(base)
        if not text:
            text, final_url = self._fetch_page(f"http://{domain}/")

        evidence = []
        if text:
            compact = re.sub(r"\s+", " ", text).strip()
            claim = compact[:700]
            evidence.append({
                "id": f"research-{domain.replace('.', '-')}-home",
                "claim": claim,
                "source_url": final_url,
                "source_type": "company_website",
                "confidence": 0.90,
            })

        careers_candidates = ["careers", "jobs", "about/careers", "company/careers"]
        careers_url = None
        careers_text = ""
        for path in careers_candidates:
            candidate = urljoin(base, path)
            careers_text, careers_final = self._fetch_page(candidate)
            if careers_text:
                careers_url = careers_final
                evidence.append({
                    "id": f"research-{domain.replace('.', '-')}-careers",
                    "claim": re.sub(r"\s+", " ", careers_text).strip()[:500],
                    "source_url": careers_final,
                    "source_type": "careers_page",
                    "confidence": 0.92,
                })
                break

        combined = f"{text}\n{careers_text}"
        tech_stack = self._extract_tech(combined)
        description = re.sub(r"\s+", " ", text).strip()[:500] if text else f"{company_name} ({domain})"
        confidence = 0.9 if text else 0.25

        return {
            "name": company_name,
            "domain": domain,
            "description": description,
            "tech_stack": tech_stack,
            "careers_page": careers_url,
            "is_personal_email": False,
            "role": None,
            "evidence": evidence,
            "research_confidence": confidence,
            "researched_at": datetime.now(timezone.utc).isoformat(),
        }

    def research_batch(self, emails: List[str]) -> List[Dict[str, Any]]:
        return [self.research(email) for email in emails]
