"""Personalization Matcher Agent"""
from typing import List
from models.schemas import MatchScore, UserProfile, CompanyInfo, JobDescription
from config.logging import logger


class PersonalizationMatcher:
    """Matches user profile against company/job and generates talking points."""

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
            company_skills.update(jd_skills)

        talking_points = []
        strengths = []
        weaknesses = []
        improvements = []

        if company_skills:
            overlap = user_skills & company_skills
            missing = company_skills - user_skills
            
            skill_match = min((len(overlap) / max(len(company_skills), 1)) * 100, 100)
            
            if overlap:
                talking_points.append(f"Strong alignment in {', '.join(sorted(overlap))}")
                strengths.append(f"Matches {len(overlap)} key skills: {', '.join(sorted(overlap))}")
            if missing:
                weaknesses.append(f"Missing: {', '.join(sorted(missing))}")
                improvements.append("Highlight transferable skills and willingness to learn")
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

        overall = (company_fit + skill_match) / 2

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