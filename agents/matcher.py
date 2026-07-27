"""Personalization Matcher Agent"""
from typing import List
from models.schemas import MatchScore, UserProfile, CompanyInfo, JobDescription
from config.logging import logger


class PersonalizationMatcher:
    """Matches user profile against company/job and generates talking points."""

    SKILL_WEIGHTS = {
        "python": 5,
        "fastapi": 5,
        "machine learning": 5,
        "deep learning": 5,
        "tensorflow": 5,
        "pytorch": 5,
        "langchain": 5,
        "langgraph": 5,
        "docker": 4,
        "postgresql": 4,
        "mongodb": 3,
        "redis": 3,
        "aws": 4,
        "azure": 3,
        "gcp": 3,
        "react": 3,
        "javascript": 2,
        "typescript": 2,
        "html": 1,
        "css": 1,
}

    def __init__(self):
        pass

    def match(self, profile: UserProfile, company: CompanyInfo, job: JobDescription = None) -> MatchScore:
        """Calculate match score between profile and company/job."""
        logger.info(f"Matching {profile.name} against {company.name}...")

        user_skills = set(s.lower().strip() for s in profile.skills if s.strip())
        company_skills = set(s.lower().strip() for s in company.tech_stack if s.strip())
        
        # Add JD skills to company skills
        jd_skills = set()
        if job and job.required_skills:
            jd_skills = set(s.lower().strip() for s in job.required_skills if s.strip())
            company_skills = {
                skill.strip().lower()
                for skill in company_skills.union(jd_skills)
            }

        talking_points = []
        strengths = []
        weaknesses = []
        improvements = []

        if company_skills:
            overlap = user_skills & company_skills
            missing = company_skills - user_skills
            
            matched_weight = sum(
                self.SKILL_WEIGHTS.get(skill, 2)
                for skill in overlap
            )

            total_weight = sum(
                self.SKILL_WEIGHTS.get(skill, 2)
                for skill in company_skills
            )

            skill_match = (
                (matched_weight / max(total_weight, 1)) * 100
            )
            
            if overlap:
                top_overlap = sorted(
                    overlap,
                    key=lambda s: self.SKILL_WEIGHTS.get(s, 2),
                    reverse=True,
                )

                if top_overlap:
                    talking_points.append(
                        "Strong alignment in "
                        + ", ".join(top_overlap[:5])
                    )
                strengths.append(
                    f"Matches {len(overlap)} important skills: "+ ", ".join(top_overlap[:5]))

            critical_missing = sorted(
                missing,key=lambda s: self.SKILL_WEIGHTS.get(s, 2),reverse=True,)

            if critical_missing:
                weaknesses.append(
                    "Missing high-priority skills: "
                    + ", ".join(critical_missing[:5])
                )

                improvements.append(
                    "Highlight transferable experience related to "
                    + critical_missing[0]
                )
        else:
            skill_match = 60.0
            talking_points.append(f"Interested in {company.name}'s mission and growth")

        # JD-specific talking points
        if job and job.responsibilities:
            resp = job.responsibilities[0]
            talking_points.append(f"Role involves: {resp[:80]}...")
        
        if job and job.experience_level:
            talking_points.append(f"Position requires {job.experience_level}")

        # Company fit based on industry/domain relevance
        company_fit = 75.0
        if profile.objective and company.industry:
            if company.industry.lower() in profile.objective.lower():
                company_fit = 90.0
                talking_points.append(f"Career objective aligns with {company.industry}")

        overall = (skill_match * 0.7 +company_fit * 0.3)

        if skill_match >= 90:
            talking_points.append("Excellent technical alignment with the role.")

        elif skill_match >= 75:
            talking_points.append
            ("Strong technical fit for this opportunity.")

        elif skill_match >= 60:
            talking_points.append
            ("Good foundation with transferable technical skills.")

        # confidence = "Low"

        # if skill_match >= 85:
        #     confidence = "High"
        # elif skill_match >= 60:
        #     confidence = "Medium"

        return MatchScore(
            company_fit=round(company_fit, 1),
            skill_match=round(skill_match, 1),
            overall_score=round(overall, 1),
            talking_points=talking_points,
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
        )

    def match_batch(self, profile: UserProfile, companies: List[CompanyInfo], jobs: List[JobDescription] = None) -> List[MatchScore]:
        if jobs is None:
            jobs = [None] * len(companies)
        return [self.match(profile, c, j) for c, j in zip(companies, jobs)]