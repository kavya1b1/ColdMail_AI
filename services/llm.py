"""LLM service with evidence-aware structured generation and review."""
import json
import os
import re
from typing import Optional, Any, Dict, List

from groq import Groq
from dotenv import load_dotenv

from config.logging import logger
from models.ai_schemas import GeneratedEmailDraft, EmailReviewResult

load_dotenv()


class LLMService:
    """Generate and review content with strict Pydantic validation."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)

    @staticmethod
    def _json_object(text: str) -> Optional[dict]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    def generate_email(
        self, profile_name: str, profile_degree: str, profile_college: str,
        profile_grad_year: int, profile_skills: list, profile_objective: str,
        profile_links: dict, company_name: str, company_description: str,
        company_industry: str, role: str, talking_points: list, tone: str,
        is_personal_email: bool = False, job: Any = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[GeneratedEmailDraft]:
        """Generate a structured, evidence-grounded draft."""
        if not self.is_available():
            return None

        evidence = evidence or []
        evidence_text = "\n".join(
            f"[{item.get('id')}] {item.get('claim')} (source: {item.get('source_url')})"
            for item in evidence[:8]
        ) or "No verified company evidence available. Do not invent company-specific facts."
        job_text = getattr(job, "raw_text", "")[:1800] if job else ""
        requirements = getattr(job, "required_skills", []) if job else []

        prompt = f"""Return ONLY valid JSON matching this exact schema:
{{"subject":"string","body":"string","key_points_used":["string"],"evidence_ids":["string"]}}

Candidate: {profile_name}, {profile_degree} at {profile_college}, graduating {profile_grad_year}
Skills: {', '.join(profile_skills[:12])}
Objective: {profile_objective}
Role: {role}
Company: {company_name}
Industry: {company_industry or 'unknown'}
Description: {company_description or 'unknown'}
Tone: {tone}
Required skills: {', '.join(requirements)}
JD excerpt: {job_text}

VERIFIED COMPANY EVIDENCE:
{evidence_text}

RELEVANT CANDIDATE TALKING POINTS:
{chr(10).join('- ' + x for x in talking_points[:8])}

Rules:
- Never invent company facts, products, news, technologies, people, or culture.
- Company-specific claims may ONLY be supported by the verified evidence above.
- If evidence is absent, use a neutral opening rather than fabricating personalization.
- Do not claim experience or skills the candidate does not have.
- Keep the body concise, human, specific, and professional (120-220 words).
- Use at most 2 evidence-backed company claims.
- Include exactly one clear CTA.
- Do not use generic filler such as "I hope this email finds you well".
- evidence_ids must contain only IDs actually used in the body.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise, evidence-grounded outreach writer."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            parsed = self._json_object(response.choices[0].message.content.strip())
            return GeneratedEmailDraft.model_validate(parsed) if parsed else None
        except Exception as exc:
            logger.error("Structured email generation failed: %s", exc)
            return None

    def review_email(self, body: str, evidence: Optional[List[Dict[str, Any]]] = None) -> Optional[EmailReviewResult]:
        """Review an email for quality and unsupported claims."""
        if not self.is_available():
            return None
        evidence_text = "\n".join(
            f"[{e.get('id')}] {e.get('claim')}" for e in (evidence or [])[:10]
        ) or "No evidence supplied."
        prompt = f"""Return ONLY valid JSON with fields: grammar_score, professionalism_score, personalization_score, clarity_score, evidence_grounding_score, hallucination_risk, spam_risk, overall_score, suggestions, unsupported_claims, needs_rewrite.

EMAIL:
{body}

VERIFIED EVIDENCE:
{evidence_text}

Score 1-10. Identify company-specific claims that are not supported by the evidence. hallucination_risk and spam_risk are 0-10 (higher is worse). Set needs_rewrite true if unsupported claims exist, hallucination_risk >= 4, personalization < 6, or overall_score < 7."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a strict email quality evaluator."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            parsed = self._json_object(response.choices[0].message.content.strip())
            return EmailReviewResult.model_validate(parsed) if parsed else None
        except Exception as exc:
            logger.error("Email review failed: %s", exc)
            return None
