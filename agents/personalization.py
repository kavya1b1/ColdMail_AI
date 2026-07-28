"""
AI Personalization Agent

Creates a strategic personalization plan before the Writer
generates the cold email.
"""

from models.schemas import (
    UserProfile,
    CompanyInfo,
    JobDescription,
    MatchScore,
    PersonalizationPlan,
)
from services.llm import LLMService


class PersonalizationAgent:
    """Generates a structured personalization strategy."""

    def __init__(self):
        self.llm = LLMService()

    def generate(
        self,
        profile: UserProfile,
        company: CompanyInfo,
        job: JobDescription,
        match: MatchScore,
        rag_context: str = "",
    ) -> PersonalizationPlan:

        prompt = f"""
You are an expert AI Career Strategist.

Your task is NOT to write an email.

Instead create a strategic personalization plan.

========================
Candidate
========================

{profile.to_context()}

========================
Company
========================

{company.to_context()}

========================
Job Description
========================

Title:
{job.title}

Required Skills:
{", ".join(job.required_skills)}

Preferred Skills:
{", ".join(job.preferred_skills)}

Responsibilities:
{", ".join(job.responsibilities)}

========================
Match Analysis
========================

Overall Match:
{match.overall_score}

Strengths:
{", ".join(match.strengths)}

Weaknesses:
{", ".join(match.weaknesses)}

Talking Points:
{", ".join(match.talking_points)}

========================
Previous Successful Emails
========================

{rag_context}

========================

Return ONLY valid JSON.

Format:

{{
    "company_summary": "...",
    "personalization_strategy": "...",
    "opening_hook": "...",
    "projects_to_highlight": [],
    "skills_to_emphasize": [],
    "skills_to_avoid": [],
    "tone": "...",
    "key_strength": "...",
    "reason_for_selection": "..."
}}

No markdown.

No explanation.

Only JSON.
"""

        response = self.llm.generate_personalization_plan(prompt)
        
        try:
            return PersonalizationPlan.model_validate_json(response)

        except Exception:

            return PersonalizationPlan(
                company_summary=company.description or "",
                personalization_strategy="Highlight strongest AI experience.",
                opening_hook=f"Mention {company.name}.",
                projects_to_highlight=[],
                skills_to_emphasize=profile.skills[:5],
                skills_to_avoid=[],
                tone=profile.tone.value,
                key_strength="AI Development",
                reason_for_selection="Fallback strategy",
            )