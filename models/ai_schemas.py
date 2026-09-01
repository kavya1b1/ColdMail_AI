"""Structured schemas used by AI agents and evidence pipelines."""
from typing import List, Optional
from pydantic import BaseModel, Field


class GeneratedEmailDraft(BaseModel):
    """Strict LLM output for an email draft."""
    subject: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=20)
    key_points_used: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class ResearchEvidence(BaseModel):
    """A factual claim with a traceable public source."""
    id: str
    claim: str
    source_url: str
    source_type: str = "company_website"
    confidence: float = Field(default=0.8, ge=0, le=1)


class ResearchResult(BaseModel):
    """Structured company research result."""
    company_name: str
    domain: str
    description: Optional[str] = None
    industry: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    careers_page: Optional[str] = None
    evidence: List[ResearchEvidence] = Field(default_factory=list)
    research_confidence: float = Field(default=0.0, ge=0, le=1)
    researched_at: str


class EmailReviewResult(BaseModel):
    """Strict LLM output for email quality review."""
    grammar_score: int = Field(ge=1, le=10)
    professionalism_score: int = Field(ge=1, le=10)
    personalization_score: int = Field(ge=1, le=10)
    clarity_score: int = Field(ge=1, le=10)
    evidence_grounding_score: int = Field(ge=1, le=10)
    hallucination_risk: int = Field(ge=0, le=10)
    spam_risk: int = Field(ge=0, le=10)
    overall_score: int = Field(ge=1, le=10)
    suggestions: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    needs_rewrite: bool = False
