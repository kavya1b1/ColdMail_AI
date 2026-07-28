"""Pydantic schemas for API validation"""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class CampaignGoal(str, Enum):
    INTERNSHIP = "internship"
    FULL_TIME = "full_time"
    REFERRAL = "referral"


class Tone(str, Enum):
    PROFESSIONAL = "professional"
    CONFIDENT = "confident"
    HUMBLE = "humble"
    ENTHUSIASTIC = "enthusiastic"


class UserProfile(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    resume_path: Optional[str] = None
    college: str
    degree: str
    graduation_year: int
    skills: List[str] = Field(default_factory=list)
    objective: str
    tone: Tone = Tone.PROFESSIONAL

    def to_context(self) -> str:
        parts = [
            f"Name: {self.name}",
            f"Education: {self.degree} at {self.college}, graduating {self.graduation_year}",
            f"Skills: {', '.join(self.skills)}",
            f"Objective: {self.objective}",
        ]
        if self.linkedin:
            parts.append(f"LinkedIn: {self.linkedin}")
        if self.github:
            parts.append(f"GitHub: {self.github}")
        if self.portfolio:
            parts.append(f"Portfolio: {self.portfolio}")
        return "\n".join(parts)


class CompanyInfo(BaseModel):
    name: str
    domain: str
    description: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    recent_news: Optional[str] = None
    culture_notes: Optional[str] = None
    careers_page: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None                    # ← NEW
    is_personal_email: bool = False               # ← NEW

    def to_context(self) -> str:
        parts = [f"Company: {self.name}"]
        if self.role:
            parts.append(f"Role: {self.role}")
        if self.description:
            parts.append(f"About: {self.description}")
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        if self.tech_stack:
            parts.append(f"Tech Stack: {', '.join(self.tech_stack)}")
        if self.recent_news:
            parts.append(f"Recent News: {self.recent_news}")
        if self.culture_notes:
            parts.append(f"Culture: {self.culture_notes}")
        if self.company_size:
            parts.append(f"Size: {self.company_size}")
        return "\n".join(parts)


class PersonalizationMatch(BaseModel):
    skill_matches: List[str] = Field(default_factory=list)
    talking_points: List[str] = Field(default_factory=list)
    hook: Optional[str] = None
    relevance_score: int = Field(default=5, ge=1, le=10)


class GeneratedEmail(BaseModel):
    recipient_email: str
    company_name: str
    subject: str
    body: str
    personalization_score: int
    key_points_used: List[str] = Field(default_factory=list)
    role: Optional[str] = None                    # ← NEW
    resume_attached: bool = False                 # ← NEW
    approved: bool = False
    sent: bool = False
    sent_at: Optional[datetime] = None


class EmailCampaign(BaseModel):
    id: str
    goal: CampaignGoal
    recipients: List[str]
    emails: List[GeneratedEmail] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    status: Literal["draft", "reviewing", "sending", "sent", "failed"] = "draft"
    stats: Dict[str, Any] = Field(default_factory=dict)


class ResumeParseResult(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    raw_text: Optional[str] = None


class JobDescription(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None


class MatchScore(BaseModel):
    company_fit: float = Field(ge=0, le=100)
    skill_match: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    talking_points: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)


class EmailReview(BaseModel):
    grammar_score: int = Field(ge=1, le=10)
    professionalism_score: int = Field(ge=1, le=10)
    spam_score: int = Field(ge=1, le=10)
    personalization_score: int = Field(ge=1, le=10)
    clarity_score: int = Field(ge=1, le=10)
    length_score: int = Field(ge=1, le=10)
    overall_score: float = Field(ge=1, le=10)
    suggestions: List[str] = Field(default_factory=list)
    needs_rewrite: bool = False


class CampaignStats(BaseModel):
    total_emails: int = 0
    sent: int = 0
    failed: int = 0
    replies: int = 0
    response_rate: float = 0.0
    avg_personalization: float = 0.0
    top_industries: List[str] = Field(default_factory=list)
    top_companies: List[str] = Field(default_factory=list)


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"