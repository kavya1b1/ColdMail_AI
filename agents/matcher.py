"""Semantic resume-to-JD/company matcher."""
from typing import List
import re

from sentence_transformers import SentenceTransformer

from models.schemas import MatchScore, UserProfile, CompanyInfo, JobDescription
from config.logging import logger
from config.settings import settings


class PersonalizationMatcher:
    """Hybrid matcher using exact skill overlap plus semantic similarity."""

    def __init__(self):
        self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)

    @staticmethod
    def _normalize(skill: str) -> str:
        skill = re.sub(r"\s+", " ", skill.lower().strip())
        aliases = {
            "gen ai": "generative ai",
            "genai": "generative ai",
            "llms": "llm",
            "large language models": "llm",
            "restful api": "rest api",
            "rest apis": "rest api",
            "postgres": "postgresql",
            "js": "javascript",
        }
        return aliases.get(skill, skill)

    def _semantic_similarity(self, profile: UserProfile, job: JobDescription | None) -> float:
        if not job:
            return 0.0
        resume_text = " ".join(profile.skills) + " " + profile.objective
        job_text = " ".join(job.required_skills + job.preferred_skills + job.tech_stack + job.responsibilities)
        if not resume_text.strip() or not job_text.strip():
            return 0.0
        vectors = self.embedder.encode([resume_text, job_text], normalize_embeddings=True)
        return max(0.0, min(100.0, float(vectors[0] @ vectors[1]) * 100.0))

    def match(self, profile: UserProfile, company: CompanyInfo, job: JobDescription = None) -> MatchScore:
        logger.info("Matching %s against %s...", profile.name, company.name)

        resume_skills = {self._normalize(s) for s in profile.skills if s.strip()}
        target_skills = {self._normalize(s) for s in (company.tech_stack + (job.required_skills if job else []) + (job.tech_stack if job else [])) if s.strip()}
        preferred = {self._normalize(s) for s in (job.preferred_skills if job else []) if s.strip()}

        exact = resume_skills & target_skills
        missing = target_skills - resume_skills
        required = {self._normalize(s) for s in (job.required_skills if job else []) if s.strip()}
        required_match = (len(resume_skills & required) / len(required) * 100) if required else (len(exact) / len(target_skills) * 100 if target_skills else 60.0)
        preferred_match = (len(resume_skills & preferred) / len(preferred) * 100) if preferred else 0.0
        semantic = self._semantic_similarity(profile, job)

        if job and required:
            skill_match = 0.55 * required_match + 0.15 * preferred_match + 0.30 * semantic
        else:
            skill_match = 0.65 * required_match + 0.35 * semantic

        company_fit = 75.0
        if profile.objective and company.industry and company.industry.lower() in profile.objective.lower():
            company_fit = 90.0

        project_relevance = min(100.0, semantic + 10.0) if semantic else float(skill_match)
        overall = 0.50 * skill_match + 0.25 * company_fit + 0.25 * project_relevance

        talking_points = []
        if exact:
            talking_points.append("Direct skill alignment: " + ", ".join(sorted(exact)))
        if semantic >= 70:
            talking_points.append("Strong semantic alignment between the candidate background and role requirements")
        if company.industry:
            talking_points.append(f"Target company operates in {company.industry}")
        if job and job.responsibilities:
            talking_points.append(f"Relevant responsibility: {job.responsibilities[0][:120]}")

        strengths = [f"Matches {len(exact)} target skills: {', '.join(sorted(exact))}"] if exact else []
        weaknesses = [f"Potential gaps: {', '.join(sorted(missing))}"] if missing else []
        improvements = ["Emphasize transferable experience for missing skills"] if missing else []

        return MatchScore(
            company_fit=round(company_fit, 1),
            skill_match=round(max(0, min(100, skill_match)), 1),
            overall_score=round(max(0, min(100, overall)), 1),
            talking_points=talking_points,
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
        )

    def match_batch(self, profile: UserProfile, companies: List[CompanyInfo], jobs: List[JobDescription] = None) -> List[MatchScore]:
        jobs = jobs or [None] * len(companies)
        return [self.match(profile, c, j) for c, j in zip(companies, jobs)]
