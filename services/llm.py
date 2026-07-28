"""Groq LLM Service"""

from __future__ import annotations

import os
import time
import re

from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq

from config.logging import logger

load_dotenv()


class LLMService:
    """
    Production-ready wrapper around Groq.

    Responsibilities
    ----------------
    • Prompt management
    • Retry logic
    • Response validation
    • Response cleaning
    • Token budgeting
    • Config management

    Public API intentionally stays compatible with the existing project.
    """

    DEFAULT_MODEL = "llama-3.1-8b-instant"

    EMAIL_TEMPERATURE = 0.65
    SUBJECT_TEMPERATURE = 0.80
    REVIEW_TEMPERATURE = 0.20

    EMAIL_MAX_TOKENS = 900
    SUBJECT_MAX_TOKENS = 60

    MAX_RETRIES = 3

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY", "")

        self.client = (
            Groq(api_key=self.api_key)
            if self.api_key
            else None
        )

        self.model = os.getenv(
            "GROQ_MODEL",
            self.DEFAULT_MODEL,
        )

        logger.info(
            "LLMService initialized | Model=%s",
            self.model,
        )

    ####################################################################
    # Public
    ####################################################################

    def is_available(self) -> bool:
        return (
            self.client is not None
            and bool(self.api_key)
        )

    ####################################################################
    # Core Generator
    ####################################################################

    def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:

        if not self.is_available():

            logger.warning(
                "Groq API unavailable."
            )

            return None

        last_exception = None

        for attempt in range(
            1,
            self.MAX_RETRIES + 1,
        ):

            try:

                logger.info(
                    "Groq request (%d/%d)",
                    attempt,
                    self.MAX_RETRIES,
                )

                response = (
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                )

                if (
                    not response.choices
                    or response.choices[0].message is None
                ):

                    raise RuntimeError(
                        "Empty response from Groq."
                    )

                content = (
                    response.choices[0]
                    .message.content
                )

                content = self._clean_response(
                    content
                )

                if not self._validate_response(
                    content
                ):
                    raise RuntimeError(
                        "Generated response failed validation."
                    )

                return content

            except Exception as e:

                last_exception = e

                logger.warning(
                    "Groq attempt %d failed: %s",
                    attempt,
                    e,
                )

                if attempt < self.MAX_RETRIES:

                    time.sleep(attempt)

        logger.error(
            "Groq generation failed after retries: %s",
            last_exception,
        )

        return None

    ####################################################################
    # Cleaning
    ####################################################################

    def _clean_response(
        self,
        text: Optional[str],
    ) -> str:

        if not text:
            return ""

        text = text.strip()

        text = re.sub(
            r"^```.*?\n",
            "",
            text,
            flags=re.DOTALL,
        )

        text = text.replace(
            "```",
            "",
        )

        prefixes = [
            "Email:",
            "Subject:",
            "Body:",
        ]

        for prefix in prefixes:

            if text.startswith(prefix):

                text = text[
                    len(prefix):
                ].strip()

        text = text.replace(
            "\r",
            "",
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    ####################################################################
    # Validation
    ####################################################################

    def _validate_response(
        self,
        text: str,
    ) -> bool:

        if not text:
            return False

        if len(text) < 30:
            return False

        banned = [
            "As an AI",
            "I am an AI",
            "Language model",
            "OpenAI",
            "Groq",
            "Here's your email",
        ]

        lower = text.lower()

        for phrase in banned:

            if phrase.lower() in lower:

                return False

        return True

    ####################################################################
    # Prompt Helpers
    ####################################################################

    def _limit_text(
        self,
        text: str,
        max_chars: int,
    ) -> str:

        if not text:
            return ""

        if len(text) <= max_chars:
            return text

        return (
            text[:max_chars]
            + "\n..."
        )

    def _skills_to_text(
        self,
        skills: List[str],
        limit: int = 6,
    ) -> str:

        if not skills:
            return "Relevant technologies"

        return ", ".join(
            skills[:limit]
        )

    def _links_to_text(
        self,
        links: Dict[str, str],
    ) -> str:

        if not links:
            return ""

        output = []

        if links.get("linkedin"):
            output.append(
                f"LinkedIn: {links['linkedin']}"
            )

        if links.get("github"):
            output.append(
                f"GitHub: {links['github']}"
            )

        if links.get("portfolio"):
            output.append(
                f"Portfolio: {links['portfolio']}"
            )

        return "\n".join(output)

    def _talking_points(
        self,
        talking_points: List[str],
    ) -> str:

        if not talking_points:

            return (
                "- Interested in the company"
            )

        return "\n".join(
            f"- {point}"
            for point in talking_points[:10]
        )
    
        ####################################################################
    # Email Prompt Builders
    ####################################################################

    def _build_email_system_prompt(
        self,
        is_personal_email: bool,
    ) -> str:

        if is_personal_email:

            return """
You are an expert networking coach.

Write emails that sound like they were written by a real student.

Rules:

- Never sound like AI.
- Never exaggerate.
- Never invent experience.
- Never use clichés.
- Be warm and respectful.
- Keep paragraphs short.
- Avoid corporate buzzwords.
- Sound natural.
- Under 250 words.

Return ONLY the email body.
"""

        return """
You are an experienced technical recruiter and professional career coach.

Your job is to write highly personalised cold emails for internship/job applications.

Rules:

- Never fabricate projects or experience.
- Never claim knowledge the candidate doesn't have.
- Never use AI clichés.
- Never write generic openings.
- Show genuine interest in the company.
- Use information from the job description whenever available.
- Mention relevant technologies naturally.
- Explain WHY the candidate fits.
- Mention attached resume.
- Finish with a confident CTA.

Style:

- Human
- Concise
- Professional
- Authentic
- 200–350 words

Return ONLY the email body.
"""

    def _build_email_user_prompt(
        self,
        *,
        profile_name,
        profile_degree,
        profile_college,
        profile_grad_year,
        profile_skills,
        profile_objective,
        profile_links,
        company_name,
        company_description,
        company_industry,
        role,
        talking_points,
        tone,
        job=None,
        is_personal_email=False,
    ) -> str:

        skills = self._skills_to_text(profile_skills)

        links = self._links_to_text(profile_links)

        talking = self._talking_points(talking_points)

        jd_text = ""

        if job:

            if getattr(job, "title", None):

                jd_text += (
                    f"\nJob Title:\n{job.title}\n"
                )

            if getattr(job, "raw_text", None):

                jd_text += (
                    "\nJob Description:\n"
                    + self._limit_text(
                        job.raw_text,
                        1800,
                    )
                )

            if getattr(job, "tech_stack", None):

                jd_text += (
                    "\nRequired Technologies:\n"
                    + ", ".join(
                        job.tech_stack[:12]
                    )
                )

            if getattr(job, "required_skills", None):

                jd_text += (
                    "\nRequired Skills:\n"
                    + ", ".join(
                        job.required_skills[:12]
                    )
                )

            if getattr(job, "responsibilities", None):

                jd_text += (
                    "\nResponsibilities:\n"
                    + "\n".join(
                        "- " + x
                        for x in job.responsibilities[:6]
                    )
                )

        if is_personal_email:

            return f"""
Candidate

Name:
{profile_name}

Education:
{profile_degree}

College:
{profile_college}

Graduation:
{profile_grad_year}

Skills:
{skills}

Career Objective:
{profile_objective}

Links:
{links}

Reason for reaching out:
{talking}

Tone:
{tone}

Recipient:
{company_name}

Requirements

1. Start with Hi.
2. Introduce yourself naturally.
3. Mention why you're reaching out.
4. Keep it friendly.
5. Ask for advice or guidance.
6. Mention resume.
7. Finish professionally.
"""

        return f"""
Candidate

Name:
{profile_name}

Education:
{profile_degree}

College:
{profile_college}

Graduation:
{profile_grad_year}

Skills:
{skills}

Career Objective:
{profile_objective}

Professional Links:
{links}

Company

Name:
{company_name}

Industry:
{company_industry}

Description:
{company_description}

Role:
{role}

Job Information:
{jd_text}

Reasons for applying:
{talking}

Preferred Tone:
{tone}

Requirements

1. Greeting should feel natural.
2. Strong opening paragraph.
3. Explain genuine interest.
4. Connect projects and skills.
5. Reference the job description.
6. Mention technologies naturally.
7. Mention attached resume.
8. End with a clear CTA.
9. Do NOT sound like AI.
10. Do NOT use generic openings.
11. Maximum 350 words.
"""

    ####################################################################
    # Email Generation
    ####################################################################

    def generate_email(
        self,
        profile_name: str,
        profile_degree: str,
        profile_college: str,
        profile_grad_year: int,
        profile_skills: list,
        profile_objective: str,
        profile_links: dict,
        company_name: str,
        company_description: str,
        company_industry: str,
        role: str,
        talking_points: list,
        tone: str,
        personalization_plan=None,
        is_personal_email: bool = False,
        job: Any = None,
        rag_context: str = ""

    ) -> Optional[str]:

        if not self.is_available():

            logger.warning(
                "LLM unavailable."
            )

            return None

        logger.info(
            "Generating email for %s",
            company_name,
        )

        system_prompt = (
            self._build_email_system_prompt(
                is_personal_email
            )
        )

        user_prompt = (
            self._build_email_user_prompt(
                profile_name=profile_name,
                profile_degree=profile_degree,
                profile_college=profile_college,
                profile_grad_year=profile_grad_year,
                profile_skills=profile_skills,
                profile_objective=profile_objective,
                profile_links=profile_links,
                company_name=company_name,
                company_description=company_description,
                company_industry=company_industry,
                role=role,
                talking_points=talking_points,
                tone=tone,
                job=job,
                is_personal_email=is_personal_email,
            )
        )
        if personalization_plan:

            user_prompt += f"""

        Personalization Strategy
        ------------------------

        Opening Hook:
        {personalization_plan.opening_hook}

        Primary Strength:
        {personalization_plan.key_strength}

        Projects To Highlight:
        {", ".join(personalization_plan.projects_to_highlight)}

        Skills To Emphasize:
        {", ".join(personalization_plan.skills_to_emphasize)}

        Skills To Avoid:
        {", ".join(personalization_plan.skills_to_avoid)}

        Overall Strategy:
        {personalization_plan.personalization_strategy}

        Reason:
        {personalization_plan.reason_for_selection}

        Use this strategy when writing the email.

        Do NOT mention this planning process.
        """
            
        if rag_context:

            user_prompt += f"""

        Previous Successful Emails
        --------------------------
        {rag_context}

        Use these previous emails only as inspiration.

        Do NOT copy them.

        Generate a fresh, personalised email based on the current company and role.
        """

        email = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.EMAIL_TEMPERATURE,
            max_tokens=self.EMAIL_MAX_TOKENS,
        )

        if email:

            logger.info(
                "Email successfully generated."
            )

        return email
    

    ####################################################################
    # Subject Prompt Builder
    ####################################################################

    def _build_subject_prompt(
        self,
        profile_name: str,
        role: str,
        company_name: str,
        is_personal: bool,
    ) -> tuple[str, str]:

        system_prompt = """
You are an expert recruiter.

Generate professional email subject lines.

Rules:

- Maximum 60 characters
- Professional
- Human sounding
- No quotes
- No markdown
- No ALL CAPS
- No emojis
- No excessive punctuation

Return ONLY the subject.
"""

        if is_personal:

            user_prompt = f"""
Generate a networking email subject.

Candidate:
{profile_name}

Recipient:
{company_name}

Goal:
Networking / career advice.
"""

        else:

            user_prompt = f"""
Generate an internship/job application subject.

Candidate:
{profile_name}

Company:
{company_name}

Role:
{role}
"""

        return system_prompt, user_prompt

    ####################################################################
    # Subject Generation
    ####################################################################

    def generate_subject(
        self,
        profile_name: str,
        role: str,
        company_name: str,
        is_personal: bool = False,
    ) -> str:

        if not self.is_available():

            if is_personal:
                return (
                    f"{profile_name} | Seeking Guidance"
                )

            return (
                f"{role} Application | {profile_name}"
            )

        logger.info(
            "Generating subject for %s",
            company_name,
        )

        system_prompt, user_prompt = (
            self._build_subject_prompt(
                profile_name,
                role,
                company_name,
                is_personal,
            )
        )

        subject = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.SUBJECT_TEMPERATURE,
            max_tokens=self.SUBJECT_MAX_TOKENS,
        )

        if not subject:

            if is_personal:
                return (
                    f"{profile_name} | Seeking Guidance"
                )

            return (
                f"{role} Application | {profile_name}"
            )

        subject = subject.replace('"', "").strip()

        if len(subject) > 60:
            subject = subject[:60].rstrip()

        return subject
    
    ####################################################################
    # Personalization Plan Generation
    ####################################################################

    def generate_personalization_plan(
        self,
        prompt: str,
    ) -> Optional[str]:
        """
        Generate a JSON personalization plan.
        """

        system_prompt = """
    You are an expert AI Career Strategist.

    You NEVER write emails.

    Your only responsibility is to analyse the candidate,
    company and job description, then produce a structured
    personalization strategy.

    Return ONLY valid JSON.

    Do not wrap the JSON in markdown.
    """

        logger.info("Generating personalization plan")

        return self._generate(
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=700,
        )
    ####################################################################
    # Utility Methods
    ####################################################################

    def estimate_tokens(
        self,
        text: str,
    ) -> int:
        """
        Rough token estimate.
        """

        if not text:
            return 0

        return int(len(text) / 4)

    def truncate_for_context(
        self,
        text: str,
        max_tokens: int = 800,
    ) -> str:
        """
        Truncate long context before sending to the LLM.
        """

        if not text:
            return ""

        max_chars = max_tokens * 4

        if len(text) <= max_chars:
            return text

        return text[:max_chars] + "\n..."

    def build_context_summary(
        self,
        company_description: str,
        talking_points: list,
        job=None,
    ) -> str:
        """
        Build a lightweight context summary.
        """

        summary = []

        if company_description:
            summary.append(
                self.truncate_for_context(
                    company_description,
                    120,
                )
            )

        if talking_points:
            summary.extend(
                talking_points[:5]
            )

        if job:

            if getattr(job, "title", None):
                summary.append(
                    f"Role: {job.title}"
                )

            if getattr(job, "tech_stack", None):
                summary.append(
                    "Tech: "
                    + ", ".join(
                        job.tech_stack[:8]
                    )
                )

        return "\n".join(summary)

    ####################################################################
    # Health Check
    ####################################################################

    def health(self) -> dict:
        """
        Returns LLM configuration and availability.
        """

        return {
            "provider": "Groq",
            "available": self.is_available(),
            "model": self.model,
            "email_temperature": self.EMAIL_TEMPERATURE,
            "subject_temperature": self.SUBJECT_TEMPERATURE,
            "email_max_tokens": self.EMAIL_MAX_TOKENS,
            "subject_max_tokens": self.SUBJECT_MAX_TOKENS,
            "max_retries": self.MAX_RETRIES,
        }
    
