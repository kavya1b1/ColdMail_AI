"""Email Writer Agent"""
import re
from typing import Dict, Any, Optional
from models.schemas import GeneratedEmail, UserProfile, CompanyInfo, MatchScore, JobDescription
from services.llm import LLMService
from config.logging import logger


class EmailWriter:
    """Generates personalized cold emails."""

    def __init__(self):
        self.llm = LLMService()

    def write(
        self,
        profile: UserProfile,
        company: CompanyInfo,
        match: MatchScore,
        recipient_email: str = "",
        role: str = None,
        job: JobDescription = None,
    ) -> GeneratedEmail:
        """Generate a personalized cold email."""
        logger.info(f"Writing email for {profile.name} -> {company.name} (role: {role})")

        role_text = role or company.role or "relevant position"
        
        # Determine recipient
        if not recipient_email:
            if company.is_personal_email:
                recipient_email = f"contact@{company.domain}" if company.domain else "contact@email.com"
            else:
                recipient_email = company.careers_page or f"careers@{company.domain}" if company.domain and "." in company.domain else "contact@company.com"

        # Try AI generation first
        ai_body = None
        if self.llm.is_available():
            ai_body = self.llm.generate_email(
                profile_name=profile.name,
                profile_degree=profile.degree,
                profile_college=profile.college,
                profile_grad_year=profile.graduation_year,
                profile_skills=profile.skills,
                profile_objective=profile.objective,
                profile_links={
                    "linkedin": profile.linkedin,
                    "portfolio": profile.portfolio,
                    "github": profile.github,
                },
                company_name=company.name,
                company_description=company.description,
                company_industry=company.industry,
                role=role_text,
                talking_points=match.talking_points if match.talking_points else [f"{company.name}'s work"],
                tone=profile.tone.value if hasattr(profile.tone, 'value') else str(profile.tone),
                is_personal_email=company.is_personal_email,
                job=job,
            )
            ai_subject = self.llm.generate_subject(
                profile_name=profile.name,
                role=role_text,
                company_name=company.name,
                is_personal=company.is_personal_email,
            )
        
        if ai_body:
            body = ai_body
            subject = ai_subject
            personalization_score = min(int(match.overall_score) + 20, 95)  # Boost for AI + JD
            logger.info(f"Used AI-generated email for {company.name}")
        else:
            body, subject = self._fallback_template(profile, company, match, role_text, recipient_email, job)
            personalization_score = min(int(match.overall_score), 100)
            logger.info(f"Used fallback template for {company.name}")

        return GeneratedEmail(
            recipient_email=recipient_email,
            company_name=company.name,
            subject=subject,
            body=body,
            personalization_score=personalization_score,
            key_points_used=match.talking_points if match.talking_points else ["General interest"],
            role=role_text,
            resume_attached=True,
        )

    def _fallback_template(
        self, profile: UserProfile, company: CompanyInfo, match: MatchScore, role: str, recipient_email: str, job: JobDescription = None
    ) -> tuple:
        """Fallback template if LLM fails."""
        skills_text = ", ".join(profile.skills[:5]) if profile.skills else "relevant technologies"
        edu_text = f"{profile.degree} at {profile.college}" if profile.college else profile.degree
        talking_points = match.talking_points if match.talking_points else [f"{company.name}'s innovative work"]
        hook = talking_points[0]

        # Add JD context
        jd_section = ""
        if job and job.raw_text:
            jd_section = f"\n\nKey requirements for this role include expertise in relevant areas, and I'm confident my background aligns well with what you're looking for."

        if company.is_personal_email:
            greeting = f"Hi {company.name},"
            body = f"""{greeting}

My name is {profile.name}, and I came across your profile while researching professionals in my field.

I'm currently pursuing my {edu_text} (graduating {profile.graduation_year}), with skills in {skills_text}. I noticed {hook} and would value your insights or any opportunities you might know of.{jd_section}

I've attached my resume for your reference.

I'd love to stay connected and hear about any opportunities or advice you might have.

Best regards,
{profile.name}
{profile.linkedin or ''}
{profile.portfolio or ''}
{profile.github or ''}"""
            subject = f"{profile.name} — {profile.degree} | Looking for opportunities"
        else:
            greeting = f"Hi Team at {company.name},"
            body = f"""{greeting}

My name is {profile.name}, and I'm reaching out regarding the {role} role at {company.name}.

I was particularly drawn to {company.name} because of {hook}.

I'm currently pursuing my {edu_text} (graduating {profile.graduation_year}). My core skills include {skills_text}, and I'm eager to apply them in a real-world setting.{jd_section}

I've attached my resume for your reference, which provides more detail on my projects and experience.

I'd love the opportunity to discuss how I can contribute to your team. Would you be open to a brief conversation or interview?

Best regards,
{profile.name}
{profile.linkedin or ''}
{profile.portfolio or ''}
{profile.github or ''}"""
            subject = f"Application for {role} at {company.name} — {profile.name}"

        return body, subject

    def write_batch(
        self,
        profile: UserProfile,
        companies: list,
        matches: list,
        recipient_emails: list = None,
        roles: list = None,
        jobs: list = None,
    ) -> list:
        """Generate emails for multiple companies."""
        if jobs is None:
            jobs = [None] * len(companies)
        emails = []
        for i, (company, match) in enumerate(zip(companies, matches)):
            role = roles[i] if roles and i < len(roles) else None
            rec_email = recipient_emails[i] if recipient_emails and i < len(recipient_emails) else ""
            job = jobs[i] if jobs and i < len(jobs) else None
            emails.append(self.write(profile, company, match, recipient_email=rec_email, role=role, job=job))
        return emails