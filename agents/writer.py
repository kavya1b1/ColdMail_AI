"""Email Writer Agent"""

from typing import Dict, Any, Optional

from config.logging import logger
from models.schemas import (
    CompanyInfo,
    GeneratedEmail,
    JobDescription,
    MatchScore,
    UserProfile,
)
from services.llm import LLMService


class EmailWriter:
    """
    Responsible for generating highly personalised cold emails.

    This class contains all prompt preparation and LLM interaction.
    """

    def __init__(self):
        self.llm = LLMService()
        logger.info("EmailWriter initialized")

    def write(
        self,
        profile: UserProfile,
        company: CompanyInfo,
        match: MatchScore,
        recipient_email: str = "",
        role: str = None,
        job: JobDescription = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedEmail:

        logger.info(
            "Generating email | Company=%s | Role=%s",
            company.name,
            role,
        )

        context = context or {}

        resume_text = context.get("resume_text", "")
        jd_text = context.get("jd_text", "")
        research_results = context.get("research_results", [])
        match_context = context.get("match_context", [])
        rag_context = context.get("rag_context", "")

        role_text = (
            role
            or company.role
            or "relevant position"
        )

        recipient_email = self._resolve_recipient(
            recipient_email,
            company,
        )

        ai_body = None
        ai_subject = None

        if self.llm.is_available():

            try:

                prompt_context = self._build_prompt_context(
                    company=company,
                    match=match,
                    job=job,
                    resume_text=resume_text,
                    jd_text=jd_text,
                    research_results=research_results,
                    match_context=match_context,
                )
                print("=" * 80)
                print("RAG CONTEXT")
                print("=" * 80)
                print(rag_context)
                print("=" * 80)
                
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
                    talking_points=prompt_context["talking_points"],
                    tone=(
                        profile.tone.value
                        if hasattr(profile.tone, "value")
                        else str(profile.tone)
                    ),
                    is_personal_email=company.is_personal_email,
                    job=job,
                    rag_context=rag_context,
                )

                ai_subject = self.llm.generate_subject(
                profile_name=profile.name,
                role=role_text,
                company_name=company.name,
                is_personal=company.is_personal_email,
            )

            except Exception:

                logger.exception(
                    "LLM generation failed for %s",
                    company.name,
                )

        if ai_body:

            logger.info(
                "AI email generated for %s",
                company.name,
            )

            body = ai_body
            subject = ai_subject

            personalization_score = min(
                int(match.overall_score) + 20,
                98,
            )

        else:

            logger.info(
                "Using fallback template for %s",
                company.name,
            )

            body, subject = self._fallback_template(
                profile,
                company,
                match,
                role_text,
                recipient_email,
                job,
            )

            personalization_score = int(match.overall_score)

        return GeneratedEmail(
            recipient_email=recipient_email,
            company_name=company.name,
            subject=subject,
            body=body,
            personalization_score=personalization_score,
            key_points_used=match.talking_points,
            role=role_text,
            resume_attached=True,
        )

    def _resolve_recipient(
        self,
        recipient_email: str,
        company: CompanyInfo,
    ) -> str:

        if recipient_email:
            return recipient_email

        if company.is_personal_email:

            if company.domain:
                return f"contact@{company.domain}"

            return "contact@email.com"

        if company.domain and "." in company.domain:
            return (
                company.careers_page
                or f"careers@{company.domain}"
            )

        return "contact@company.com"

    def _build_prompt_context(
        self,
        company,
        match,
        job,
        resume_text,
        jd_text,
        research_results,
        match_context,
    ):

        talking_points = list(match.talking_points)

        talking_points.extend(match.strengths)

        talking_points.extend(match.improvements)

        if job and job.title:
            talking_points.append(
                f"Role: {job.title}"
            )

        if job and job.tech_stack:
            talking_points.append(
                "Tech Stack: "
                + ", ".join(job.tech_stack[:6])
            )

        for item in match_context:

            if item.get("company") == company.name:

                talking_points.extend(
                    item.get(
                        "matched_skills",
                        [],
                    )[:5]
                )

                break

        return {
            "resume_text": resume_text,
            "jd_text": jd_text,
            "research_results": research_results,
            "talking_points": talking_points,
        }
    
    def _fallback_template(
        self,
        profile: UserProfile,
        company: CompanyInfo,
        match: MatchScore,
        role: str,
        recipient_email: str,
        job: JobDescription = None,
    ) -> tuple[str, str]:
        """
        Fallback email template when the LLM is unavailable.
        """

        skills = ", ".join(profile.skills[:5]) if profile.skills else "relevant technologies"

        education = (
            f"{profile.degree} at {profile.college}"
            if profile.college
            else profile.degree
        )

        talking_points = (
            match.talking_points
            if match.talking_points
            else [f"{company.name}'s work"]
        )

        strengths = (
            match.strengths
            if match.strengths
            else []
        )

        improvements = (
            match.improvements
            if match.improvements
            else []
        )

        hook = talking_points[0]

        jd_section = ""

        if job:

            if job.title:
                jd_section += (
                    f"\nI was particularly interested in the **{job.title}** position."
                )

            if job.tech_stack:
                jd_section += (
                    "\nThe technologies mentioned in the job description closely align "
                    "with my experience in "
                    + ", ".join(job.tech_stack[:5])
                    + "."
                )

        strengths_section = ""

        if strengths:

            strengths_section = (
                "\nSome of my strongest matches include:\n"
                + "\n".join(f"• {s}" for s in strengths[:3])
            )

        improvement_section = ""

        if improvements:

            improvement_section = (
                "\nAlthough there are areas I continue to learn, "
                + improvements[0]
                + "."
            )

        if company.is_personal_email:

            greeting = f"Hi {company.name},"

            body = f"""{greeting}

I hope you're doing well.

My name is {profile.name}, and while researching professionals working in areas that interest me, I came across your profile.

I'm currently pursuing my {education} and will graduate in {profile.graduation_year}. My background includes {skills}.

I was especially interested in {hook}.{jd_section}

{strengths_section}

I've attached my resume and would truly appreciate any advice, feedback, or opportunities you think might be suitable.

Thank you for your time, and I hope we can stay connected.

Best regards,

{profile.name}
{profile.linkedin or ""}
{profile.github or ""}
{profile.portfolio or ""}
"""

            subject = (
                f"{profile.name} | Interested in connecting"
            )

        else:

            greeting = f"Dear Hiring Team at {company.name},"

            body = f"""{greeting}

I hope you're doing well.

My name is {profile.name}, and I am writing to express my interest in the {role} opportunity at {company.name}.

After learning more about your company, I was particularly impressed by {hook}.

I am currently pursuing my {education} and expect to graduate in {profile.graduation_year}. Throughout my projects and coursework, I have developed experience in {skills}.{jd_section}

{strengths_section}

{improvement_section}

I have attached my resume for your consideration and would be grateful for the opportunity to discuss how I could contribute to your team.

Thank you for your time and consideration. I look forward to hearing from you.

Kind regards,

{profile.name}
{profile.linkedin or ""}
{profile.github or ""}
{profile.portfolio or ""}
"""

            subject = (
                f"Application for {role} | {profile.name}"
            )

        return body, subject

    def write_batch(
        self,
        profile: UserProfile,
        companies: list,
        matches: list,
        recipient_emails: list = None,
        roles: list = None,
        jobs: list = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> list:
        """
        Generate emails for multiple companies.
        """

        if jobs is None:
            jobs = [None] * len(companies)

        emails = []

        logger.info(
            "Generating %d emails...",
            len(companies),
        )

        for index, (company, match) in enumerate(
            zip(companies, matches)
        ):

            try:

                role = (
                    roles[index]
                    if roles and index < len(roles)
                    else None
                )

                recipient = (
                    recipient_emails[index]
                    if recipient_emails
                    and index < len(recipient_emails)
                    else ""
                )

                job = (
                    jobs[index]
                    if jobs and index < len(jobs)
                    else None
                )

                email = self.write(
                    profile=profile,
                    company=company,
                    match=match,
                    recipient_email=recipient,
                    role=role,
                    job=job,
                    context=context,
                )

                emails.append(email)

            except Exception:

                logger.exception(
                    "Failed to generate email for %s",
                    getattr(company, "name", "Unknown Company"),
                )

        logger.info(
            "Successfully generated %d/%d emails",
            len(emails),
            len(companies),
        )

        return emails