"""Evidence-aware Email Writer Agent."""
from typing import Optional

from models.schemas import GeneratedEmail, UserProfile, CompanyInfo, MatchScore, JobDescription
from services.llm import LLMService


class EmailWriter:
    """Generate concise personalized emails with explicit evidence provenance."""

    def __init__(self):
        self.llm = LLMService()

    def write(self, profile: UserProfile, company: CompanyInfo, match: MatchScore,
              recipient_email: str = "", role: str = None, job: JobDescription = None,
              evidence: Optional[list] = None) -> GeneratedEmail:
        role_text = role or company.role or "relevant position"
        evidence = evidence or []
        draft = self.llm.generate_email(
            profile_name=profile.name, profile_degree=profile.degree,
            profile_college=profile.college, profile_grad_year=profile.graduation_year,
            profile_skills=profile.skills, profile_objective=profile.objective,
            profile_links={"linkedin": profile.linkedin, "portfolio": profile.portfolio, "github": profile.github},
            company_name=company.name, company_description=company.description,
            company_industry=company.industry, role=role_text,
            talking_points=match.talking_points,
            tone=profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone),
            is_personal_email=company.is_personal_email, job=job, evidence=evidence,
        ) if self.llm.is_available() else None

        if draft:
            subject, body = draft.subject, draft.body
            key_points = draft.key_points_used
            evidence_ids = [eid for eid in draft.evidence_ids if any(e.get("id") == eid for e in evidence)]
            score = min(100, int(match.overall_score + (10 if evidence_ids else 0)))
        else:
            body, subject = self._fallback_template(profile, company, match, role_text, evidence)
            key_points = match.talking_points or ["Role alignment"]
            evidence_ids = [e.get("id") for e in evidence[:1] if e.get("id")]
            score = int(match.overall_score)

        return GeneratedEmail(
            recipient_email=recipient_email, company_name=company.name,
            subject=subject, body=body, personalization_score=score,
            key_points_used=key_points, evidence_ids=evidence_ids,
            role=role_text, resume_attached=bool(profile.resume_path),
        )

    def _fallback_template(self, profile, company, match, role, evidence=None):
        skills = ", ".join(profile.skills[:5]) or "relevant technologies"
        edu = f"{profile.degree} at {profile.college}"
        hook = evidence[0].get("claim", "")[:180] if evidence else ""
        research_line = f"I was interested in {company.name} based on this public information: {hook}\n\n" if hook else ""
        body = f"""Hi Team at {company.name},

I'm {profile.name}, pursuing {edu} and graduating in {profile.graduation_year}. I'm interested in the {role} opportunity and my background includes {skills}.

{research_line}My background aligns with the role through {', '.join(match.talking_points[:2]) or 'the technical requirements of the position'}.

I've attached my resume for context. Would you be open to a brief conversation about the role or relevant opportunities on the team?

Best regards,
{profile.name}
{profile.linkedin or ''}
{profile.github or ''}"""
        return body, f"{profile.name} — {role} at {company.name}"

    def write_batch(self, profile, companies, matches, recipient_emails=None, roles=None, jobs=None, evidence=None):
        recipient_emails, roles = recipient_emails or [], roles or []
        jobs = jobs or [None] * len(companies)
        evidence = evidence or []
        emails = []
        for i, (company, match) in enumerate(zip(companies, matches)):
            role = roles[i] if i < len(roles) else None
            recipient = recipient_emails[i] if i < len(recipient_emails) else ""
            job = jobs[i] if i < len(jobs) else None
            company_evidence = [e for e in evidence if company.domain.replace('.', '-') in e.get('id', '')] or evidence
            emails.append(self.write(profile, company, match, recipient_email=recipient, role=role, job=job, evidence=company_evidence))
        return emails
