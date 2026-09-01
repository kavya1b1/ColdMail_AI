"""Parser Agent Nodes - Resume and Job Description"""
import fitz
import re
from agents.state import AgentState
from models.schemas import ResumeParseResult, JobDescription, UserProfile
from config.logging import logger


class ResumeParserNode:
    """Parse PDF resume without destroying an existing richer profile."""
    def __init__(self):
        logger.info("ResumeParserNode initialized")

    def __call__(self, state: AgentState) -> dict:
        resume_path = state.get("resume_path")
        if not resume_path:
            return {"logs": ["ResumeParser: No resume path provided"]}
        try:
            result = self._parse_pdf(resume_path)
            existing = state.get("user_profile")
            if existing and isinstance(existing, dict):
                existing = UserProfile(**existing)
            if existing:
                profile = existing.model_copy(update={
                    "name": result.name or existing.name,
                    "email": result.email or existing.email,
                    "phone": result.phone or existing.phone,
                    "linkedin": result.linkedin or existing.linkedin,
                    "github": result.github or existing.github,
                    "skills": list(dict.fromkeys(existing.skills + result.skills)),
                    "resume_path": resume_path,
                })
            else:
                profile = UserProfile(name=result.name or "", email=result.email or "", phone=result.phone,
                    linkedin=result.linkedin, github=result.github, portfolio=result.portfolio,
                    resume_path=resume_path, college="", degree="", graduation_year=2026,
                    skills=result.skills, objective="", tone="professional")
            return {"user_profile": profile, "resume_parse": result, "logs": [f"ResumeParser: Parsed resume for {result.name}"]}
        except Exception as e:
            logger.error("ResumeParser error: %s", e)
            return {"errors": [f"Resume parsing failed: {e}"], "logs": ["ResumeParser: Failed"]}

    def _parse_pdf(self, path: str) -> ResumeParseResult:
        doc = fitz.open(path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        result = ResumeParseResult(raw_text=text)
        email = re.search(r'[\w.\-+]+@[\w.\-]+\.\w+', text)
        phone = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        linkedin = re.search(r'linkedin\.com/in/[\w-]+', text, re.I)
        github = re.search(r'github\.com/[\w-]+', text, re.I)
        if email: result.email = email.group()
        if phone: result.phone = phone.group()
        if linkedin: result.linkedin = f"https://{linkedin.group()}"
        if github: result.github = f"https://{github.group()}"
        skills = ["python", "javascript", "typescript", "react", "vue", "angular", "node.js", "django", "flask", "fastapi", "java", "go", "rust", "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "postgresql", "mysql", "mongodb", "redis", "machine learning", "deep learning", "tensorflow", "pytorch", "html", "css", "sass", "tailwind", "bootstrap", "rag", "llm", "langchain", "langgraph"]
        lower = text.lower()
        result.skills = list(dict.fromkeys([s.title() if s != "node.js" else "Node.js" for s in skills if s in lower]))
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if lines: result.name = lines[0]
        return result


class JobDescriptionParserNode:
    """Parse job description text into structured fields."""
    def __init__(self):
        logger.info("JobDescriptionParserNode initialized")

    def __call__(self, state: AgentState) -> dict:
        jd = state.get("job_description")
        if not jd or not jd.raw_text:
            return {"logs": ["JDParser: No job description provided"]}
        try:
            parsed = self._parse_jd(jd.raw_text)
            return {"job_description": parsed, "parsed_jobs": [parsed], "logs": ["JDParser: Parsed successfully"]}
        except Exception as e:
            return {"errors": [f"JD parsing failed: {e}"], "logs": ["JDParser: Failed"]}

    def _parse_jd(self, text: str) -> JobDescription:
        jd = JobDescription(raw_text=text)
        patterns = [(r'(?:job title|position|role)[\s:]+([^\n]+)', "title"), (r'^(?!\s*$)([^\n]+)', "title")]
        for pattern, field in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                jd.title = m.group(1).strip(); break
        req = re.search(r'(?:requirements|required skills|qualifications)[\s:]*([\s\S]*?)(?=preferred|responsibilities|benefits|$)', text, re.I)
        pref = re.search(r'(?:preferred|nice to have|bonus)[\s:]*([\s\S]*?)(?=responsibilities|benefits|$)', text, re.I)
        resp = re.search(r'(?:responsibilities|what you.?ll do|role)[\s:]*([\s\S]*?)(?=requirements|qualifications|benefits|$)', text, re.I)
        if req: jd.required_skills = self._extract_skills(req.group(1))
        if pref: jd.preferred_skills = self._extract_skills(pref.group(1))
        if resp: jd.responsibilities = [x.strip(" -•\t") for x in resp.group(1).splitlines() if len(x.strip()) > 10]
        exp = re.search(r'(\d+)\+?\s*years?(?:\s*of)?\s*(?:experience|exp)', text, re.I)
        if exp: jd.experience_level = f"{exp.group(1)}+ years"
        jd.tech_stack = self._extract_skills(text)
        return jd

    def _extract_skills(self, text: str) -> list:
        skills = ["python", "javascript", "typescript", "react", "vue", "angular", "node.js", "django", "flask", "fastapi", "spring", "java", "go", "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "machine learning", "deep learning", "tensorflow", "pytorch", "graphql", "rest api", "microservices", "serverless", "ci/cd", "github actions", "jenkins", "gitlab", "rag", "llm", "langchain", "langgraph", "generative ai"]
        lower = text.lower()
        return list(dict.fromkeys([s.title() if s != "node.js" else "Node.js" for s in skills if s in lower]))
