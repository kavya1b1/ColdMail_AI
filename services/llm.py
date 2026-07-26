"""Groq LLM Service for AI-powered email generation"""
import os
from typing import Optional, Any
from groq import Groq
from config.logging import logger
from dotenv import load_dotenv


load_dotenv()  

class LLMService:
    """Generates personalized content using Groq LLM."""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model = "llama-3.1-8b-instant"  # Fast & cheap
    
    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)
    
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
        is_personal_email: bool = False,
        job: Any = None,  # ← NEW
    ) -> Optional[str]:
        """Generate a personalized cold email using Groq."""
        
        if not self.is_available():
            logger.warning("Groq API key not set. Falling back to template.")
            return None
        
        skills_str = ", ".join(profile_skills[:6]) if profile_skills else "various technologies"
        links_str = ""
        if profile_links.get("linkedin"):
            links_str += f"\nLinkedIn: {profile_links['linkedin']}"
        if profile_links.get("portfolio"):
            links_str += f"\nPortfolio: {profile_links['portfolio']}"
        if profile_links.get("github"):
            links_str += f"\nGitHub: {profile_links['github']}"
        
        talking_points_str = "\n".join([f"- {tp}" for tp in talking_points]) if talking_points else "- The company's innovative work"

        # Build JD context
        jd_context = ""
        if job:
            if hasattr(job, "raw_text") and job.raw_text:
                jd_context += f"\n\nJob Description Context:\n{job.raw_text[:800]}"
            if hasattr(job, "required_skills") and job.required_skills:
                jd_context += f"\n\nRequired Skills: {', '.join(job.required_skills)}"
            if hasattr(job, "responsibilities") and job.responsibilities:
                jd_context += f"\n\nKey Responsibilities: {', '.join(job.responsibilities[:3])}"

        
        if is_personal_email:
            system_prompt = """You are an expert at writing professional networking emails. 
Write a concise, warm email (150-250 words) to a professional contact. 
Be respectful of their time. Mention you're a student looking for opportunities."""
            
            user_prompt = f"""Write a personalized cold email from {profile_name} to {company_name}.

About me:
- {profile_degree} at {profile_college}, graduating {profile_grad_year}
- Skills: {skills_str}
- Career objective: {profile_objective}
- Links: {links_str}

Why I'm reaching out:
{talking_points_str}

Tone: {tone}

Requirements:
1. Start with "Hi {company_name},"
2. Mention I came across their profile
3. Briefly introduce myself (2-3 sentences)
4. Ask for advice or referrals
5. End professionally
6. Keep it under 250 words
7. Do NOT use generic filler like "I hope this email finds you well"
8. Make it sound human and authentic

Write ONLY the email body, no subject line, no explanations."""
        else:
            system_prompt = f"""You are an expert at writing cold emails for job applications.

Your goal is to produce an email that sounds genuinely written by a human after reading the company's website and job description.

If a Job Description is provided, use it heavily.

Mention:
- technologies
- responsibilities
- required skills
- domain
- products
- values

naturally throughout the email.

Never fabricate experience.

Write a compelling email between 200-350 words.
"""
            
            user_prompt = f"""Write a personalized cold email from {profile_name} applying for the {role} role at {company_name}.

About me:
- {profile_degree} at {profile_college}, graduating {profile_grad_year}
- Skills: {skills_str}
- Career objective: {profile_objective}
- Links: {links_str}

About the company:
- Name: {company_name}
- Description: {company_description or 'A growing company'}
- Industry: {company_industry or 'Technology'}

{jd_context}

- Why I'm interested:
{talking_points_str}

Tone: {tone}

Requirements:
1. Start with "Hi Team at {company_name},"
2. Hook: Mention something specific about the company or role (NOT generic)
3. Brief intro + value proposition (why I'm a good fit)
4. Specific connection between my skills and the role
5. Clear call-to-action (ask for a conversation/interview)
6. End with "Best regards,\n{profile_name}" + links
7. Mention I've attached my resume
8. Keep it 200-350 words
9. Do NOT use clichés like "I hope this email finds you well" or "To whom it may concern"
10. Make it sound like a real human wrote it, not AI
11. Reference specific skills or requirements from the job description to show I've read it carefully.

Write ONLY the email body, no subject line, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800,
            )
            email_body = response.choices[0].message.content.strip()
            logger.info(f"Groq generated email for {company_name}")
            return email_body
            
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            return None
    
    def generate_subject(self, profile_name: str, role: str, company_name: str, is_personal: bool = False) -> str:
        """Generate a catchy subject line."""
        if not self.is_available():
            return f"Application for {role} at {company_name} — {profile_name}" if not is_personal else f"{profile_name} — Looking for opportunities"
        
        prompt = f"""Write a short, catchy email subject line (max 60 characters) for a cold email from {profile_name} {'to a professional contact' if is_personal else f'applying for {role} at {company_name}'}.

Requirements:
- No ALL CAPS
- No excessive punctuation
- Professional but intriguing
- Under 60 characters

Write ONLY the subject line, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=50,
            )
            subject = response.choices[0].message.content.strip().replace('"', '')
            return subject[:60]
        except Exception as e:
            logger.error(f"Subject generation failed: {e}")
            return f"Application for {role} at {company_name} — {profile_name}"