"""LangGraph state definitions"""
from typing import TypedDict, List, Dict, Any, Optional
from models.schemas import UserProfile, CompanyInfo, MatchScore, GeneratedEmail, EmailCampaign, CampaignGoal, JobDescription, EmailReview


class AgentState(TypedDict, total=False):
    """Shared state across all LangGraph nodes."""
    user_profile: Optional[UserProfile]
    recipient_emails: List[str]
    goal: CampaignGoal
    resume_path: Optional[str]
    job_description: Optional[JobDescription]
    roles: List[str]
    job_descriptions: List[str]
    parsed_jobs: List[JobDescription]
    companies: List[CompanyInfo]
    research_evidence: List[Dict[str, Any]]
    matches: List[MatchScore]
    generated_emails: List[GeneratedEmail]
    reviews: List[EmailReview]
    needs_rewrite: List[bool]
    rewrite_attempts: int
    campaign: Optional[EmailCampaign]
    send_results: Dict[str, Any]
    next_step: str
    errors: List[str]
    logs: List[str]
    awaiting_approval: bool
    approved_indices: List[int]
    session_id: str
    timestamp: str
    matched: bool
    researched: bool
    company_researched: bool
    email_written: bool
    email_reviewed: bool
