"""Company Research Agent for ColdMail AI"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from config.logging import logger


# Common personal email domains
PERSONAL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "yahoo.in",
    "yahoo.co.in",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "protonmail.com",
    "zoho.com",
    "aol.com",
    "mail.com",
    "yandex.com",
    "qq.com",
    "163.com",
    "126.com",
    "foxmail.com",
}


COMMON_SUBDOMAINS = {
    "mail",
    "smtp",
    "mx",
    "email",
    "hr",
    "careers",
    "jobs",
    "apply",
    "team",
    "support",
    "info",
    "contact",
    "hello",
}


class CompanyResearcher:
    """
    Lightweight company research engine.

    Responsibilities

    • Email parsing
    • Personal/company detection
    • Company normalization
    • Result caching
    • Metadata enrichment
    • Safe fallbacks

    This class intentionally avoids external APIs so it
    remains fast and deterministic.
    """

    DEFAULT_DESCRIPTION = (
        "No public company description available."
    )

    def __init__(self):

        self.cache: Dict[str, Dict[str, Any]] = {}

        logger.info(
            "CompanyResearcher initialized."
        )

    ####################################################################
    # Public
    ####################################################################

    def clear_cache(self):

        self.cache.clear()

    ####################################################################
    # Helpers
    ####################################################################

    def _extract_name_from_email(
        self,
        email: str,
    ) -> str:
        """
        Convert

        john_smith23@gmail.com

        →

        John Smith
        """

        prefix = email.split("@")[0]

        cleaned = re.sub(
            r"[0-9._\-]+",
            " ",
            prefix,
        )

        words = [
            word.capitalize()
            for word in cleaned.split()
            if len(word) > 1
        ]

        if words:
            return " ".join(words)

        return prefix.capitalize()

    def _normalize_domain(
        self,
        domain: str,
    ) -> str:
        """
        Removes common subdomains.

        mail.company.com

        →

        company.com
        """

        parts = domain.lower().split(".")

        while (
            len(parts) > 2
            and parts[0] in COMMON_SUBDOMAINS
        ):
            parts.pop(0)

        return ".".join(parts)

    def _extract_company_name(
        self,
        domain: str,
    ) -> str:
        """
        Convert

        stripe.com

        →

        Stripe

        abc-tech-solutions.ai

        →

        Abc Tech Solutions
        """

        root = domain.split(".")[0]

        root = root.replace("-", " ")
        root = root.replace("_", " ")

        root = re.sub(
            r"([a-z])([A-Z])",
            r"\1 \2",
            root,
        )

        root = re.sub(
            r"\s+",
            " ",
            root,
        ).strip()

        return " ".join(
            word.capitalize()
            for word in root.split()
        )

    def _default_result(
        self,
        *,
        name: str,
        domain: str,
        is_personal: bool,
    ) -> Dict[str, Any]:

        return {
            "name": name,
            "domain": domain,
            "description": self.DEFAULT_DESCRIPTION,
            "industry": None,
            "company_size": None,
            "tech_stack": [],
            "products": [],
            "culture_keywords": [],
            "career_page": None,
            "linkedin": None,
            "role": None,
            "confidence": 0.55,
            "is_personal_email": is_personal,
        }

    def _cached(
        self,
        domain: str,
    ) -> Optional[Dict[str, Any]]:

        return self.cache.get(domain)

    def _store_cache(
        self,
        domain: str,
        result: Dict[str, Any],
    ):

        self.cache[domain] = result.copy()

    ####################################################################
    # Simple Enrichment
    ####################################################################

    def _infer_industry(
        self,
        company_name: str,
        domain: str,
    ) -> Optional[str]:

        text = (
            company_name + " " + domain
        ).lower()

        mapping = {
            "health": "Healthcare",
            "med": "Healthcare",
            "bank": "Finance",
            "fin": "Finance",
            "pay": "Financial Technology",
            "tech": "Technology",
            "cloud": "Cloud Computing",
            "ai": "Artificial Intelligence",
            "robot": "Robotics",
            "data": "Data Analytics",
            "software": "Software",
            "consult": "Consulting",
            "edu": "Education",
            "learn": "Education",
            "retail": "Retail",
            "shop": "E-Commerce",
            "commerce": "E-Commerce",
        }

        for keyword, industry in mapping.items():

            if keyword in text:
                return industry

        return None

    def _infer_tech_stack(
        self,
        company_name: str,
        domain: str,
    ) -> List[str]:

        text = (
            company_name + " " + domain
        ).lower()

        stack = []

        if "ai" in text:
            stack.extend(
                [
                    "Python",
                    "Machine Learning",
                    "LLMs",
                ]
            )

        if "cloud" in text:
            stack.extend(
                [
                    "AWS",
                    "Docker",
                    "Kubernetes",
                ]
            )

        if "data" in text:
            stack.extend(
                [
                    "SQL",
                    "Python",
                ]
            )

        if "web" in text:

            stack.extend(
                [
                    "JavaScript",
                    "React",
                ]
            )

        return sorted(
            list(set(stack))
        )
    

        ####################################################################
    # Research
    ####################################################################

    def research(
        self,
        email: str,
    ) -> Dict[str, Any]:
        """
        Research a company or individual from an email address.

        Returns a consistent metadata structure that downstream
        agents (matcher, writer, reviewer) can consume safely.
        """

        logger.info(
            "Researching %s",
            email,
        )

        email = (email or "").strip()

        if not email:

            return self._default_result(
                name="Unknown",
                domain="",
                is_personal=False,
            )

        ################################################################
        # Invalid email
        ################################################################

        if "@" not in email:

            return {
                **self._default_result(
                    name=email.capitalize(),
                    domain=email,
                    is_personal=False,
                ),
                "confidence": 0.20,
            }

        ################################################################
        # Parse
        ################################################################

        local_part, domain = email.split("@", 1)

        domain = self._normalize_domain(domain)

        ################################################################
        # Cache
        ################################################################

        cached = self._cached(domain)

        if cached is not None:

            logger.info(
                "Using cached research for %s",
                domain,
            )

            return cached.copy()

        ################################################################
        # Personal email
        ################################################################

        if domain in PERSONAL_DOMAINS:

            person_name = self._extract_name_from_email(
                email
            )

            result = {
                **self._default_result(
                    name=person_name,
                    domain=domain,
                    is_personal=True,
                ),
                "description": (
                    f"Personal contact ({person_name})"
                ),
                "confidence": 0.98,
            }

            self._store_cache(
                domain,
                result,
            )

            return result

        ################################################################
        # Company email
        ################################################################

        company_name = self._extract_company_name(
            domain
        )

        industry = self._infer_industry(
            company_name,
            domain,
        )

        tech_stack = self._infer_tech_stack(
            company_name,
            domain,
        )

        description = (
            f"{company_name} appears to be "
            f"an organisation operating"
        )

        if industry:
            description += (
                f" in the {industry} sector."
            )
        else:
            description += " in its respective industry."

        result = {
            **self._default_result(
                name=company_name,
                domain=domain,
                is_personal=False,
            ),
            "description": description,
            "industry": industry,
            "tech_stack": tech_stack,
            "confidence": 0.75,
        }

        ################################################################
        # Role inference
        ################################################################

        local_lower = local_part.lower()

        role_keywords = {
            "hr": "Human Resources",
            "jobs": "Recruitment",
            "career": "Recruitment",
            "careers": "Recruitment",
            "talent": "Talent Acquisition",
            "recruit": "Recruitment",
            "founder": "Founder",
            "ceo": "Chief Executive Officer",
            "cto": "Chief Technology Officer",
            "coo": "Chief Operating Officer",
            "manager": "Manager",
            "director": "Director",
            "support": "Support",
            "admin": "Administrator",
            "engineering": "Engineering",
            "developer": "Engineering",
            "dev": "Engineering",
            "team": "Team",
            "contact": "General Contact",
            "hello": "General Contact",
            "info": "General Contact",
        }

        for keyword, inferred_role in role_keywords.items():

            if keyword in local_lower:

                result["role"] = inferred_role
                result["confidence"] = max(
                    result["confidence"],
                    0.82,
                )
                break

        ################################################################
        # Simple company-size heuristic
        ################################################################

        if result["industry"] == "Artificial Intelligence":

            result["company_size"] = "Startup / Scale-up"

        elif result["industry"] == "Software":

            result["company_size"] = (
                "Small to Medium Enterprise"
            )

        elif result["industry"] == "Consulting":

            result["company_size"] = (
                "Medium to Large Enterprise"
            )

        ################################################################
        # Career page heuristic
        ################################################################

        result["career_page"] = (
            f"https://{domain}/careers"
        )

        result["linkedin"] = (
            f"https://www.linkedin.com/company/"
            f"{company_name.lower().replace(' ', '-')}"
        )

        ################################################################
        # Cache result
        ################################################################

        self._store_cache(
            domain,
            result,
        )

        logger.info(
            "Research complete for %s",
            company_name,
        )

        return result
    
        ####################################################################
    # Batch Research
    ####################################################################

    def research_batch(
        self,
        emails: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Research multiple email addresses.

        Each email is processed independently so one failure
        does not interrupt the remaining batch.
        """

        logger.info(
            "Researching %d email(s).",
            len(emails),
        )

        results: List[Dict[str, Any]] = []

        for email in emails:

            try:

                results.append(
                    self.research(email)
                )

            except Exception as exc:

                logger.exception(
                    "Failed researching %s: %s",
                    email,
                    exc,
                )

                results.append(
                    {
                        **self._default_result(
                            name="Unknown",
                            domain=email,
                            is_personal=False,
                        ),
                        "confidence": 0.0,
                        "error": str(exc),
                    }
                )

        logger.info(
            "Research completed. %d result(s).",
            len(results),
        )

        return results

    ####################################################################
    # Validation
    ####################################################################

    def validate_result(
        self,
        result: Dict[str, Any],
    ) -> bool:
        """
        Ensure a research result contains the minimum
        required fields.
        """

        required = [
            "name",
            "domain",
            "description",
            "industry",
            "tech_stack",
            "role",
            "confidence",
            "is_personal_email",
        ]

        return all(
            key in result
            for key in required
        )

    ####################################################################
    # Cache Utilities
    ####################################################################

    def cache_size(self) -> int:
        """
        Number of cached domains.
        """

        return len(self.cache)

    def cache_domains(self) -> List[str]:
        """
        Return cached domains.
        """

        return sorted(
            self.cache.keys()
        )

    ####################################################################
    # Statistics
    ####################################################################

    def statistics(self) -> Dict[str, Any]:
        """
        Returns useful runtime statistics.
        """

        personal = 0
        companies = 0

        for item in self.cache.values():

            if item.get(
                "is_personal_email",
                False,
            ):
                personal += 1
            else:
                companies += 1

        return {
            "cached_entries": len(
                self.cache
            ),
            "companies": companies,
            "personal_contacts": personal,
        }

    ####################################################################
    # Health Check
    ####################################################################

    def health(self) -> Dict[str, Any]:
        """
        Service health information.
        """

        return {
            "service": "CompanyResearcher",
            "status": "healthy",
            "cached_domains": len(
                self.cache
            ),
            "supports_batch": True,
            "supports_cache": True,
            "supports_industry_inference": True,
            "supports_role_inference": True,
            "supports_company_size_inference": True,
        }
    
        ####################################################################
    # Batch Research
    ####################################################################

    def research_batch(
        self,
        emails: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Research multiple email addresses.

        Each email is processed independently so one failure
        does not interrupt the remaining batch.
        """

        logger.info(
            "Researching %d email(s).",
            len(emails),
        )

        results: List[Dict[str, Any]] = []

        for email in emails:

            try:

                results.append(
                    self.research(email)
                )

            except Exception as exc:

                logger.exception(
                    "Failed researching %s: %s",
                    email,
                    exc,
                )

                results.append(
                    {
                        **self._default_result(
                            name="Unknown",
                            domain=email,
                            is_personal=False,
                        ),
                        "confidence": 0.0,
                        "error": str(exc),
                    }
                )

        logger.info(
            "Research completed. %d result(s).",
            len(results),
        )

        return results

    ####################################################################
    # Validation
    ####################################################################

    def validate_result(
        self,
        result: Dict[str, Any],
    ) -> bool:
        """
        Ensure a research result contains the minimum
        required fields.
        """

        required = [
            "name",
            "domain",
            "description",
            "industry",
            "tech_stack",
            "role",
            "confidence",
            "is_personal_email",
        ]

        return all(
            key in result
            for key in required
        )

    ####################################################################
    # Cache Utilities
    ####################################################################

    def cache_size(self) -> int:
        """
        Number of cached domains.
        """

        return len(self.cache)

    def cache_domains(self) -> List[str]:
        """
        Return cached domains.
        """

        return sorted(
            self.cache.keys()
        )

    ####################################################################
    # Statistics
    ####################################################################

    def statistics(self) -> Dict[str, Any]:
        """
        Returns useful runtime statistics.
        """

        personal = 0
        companies = 0

        for item in self.cache.values():

            if item.get(
                "is_personal_email",
                False,
            ):
                personal += 1
            else:
                companies += 1

        return {
            "cached_entries": len(
                self.cache
            ),
            "companies": companies,
            "personal_contacts": personal,
        }

    ####################################################################
    # Health Check
    ####################################################################

    def health(self) -> Dict[str, Any]:
        """
        Service health information.
        """

        return {
            "service": "CompanyResearcher",
            "status": "healthy",
            "cached_domains": len(
                self.cache
            ),
            "supports_batch": True,
            "supports_cache": True,
            "supports_industry_inference": True,
            "supports_role_inference": True,
            "supports_company_size_inference": True,
        }