"""ColdMail AI Pro — Streamlit UI with LangGraph"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import uuid
from datetime import datetime

from models.schemas import UserProfile, CampaignGoal, Tone
from agents.workflow import ColdMailWorkflow
from config.logging import logger
from utils.pdf_utils import extract_text_from_pdf


# ─── Session State ───
if "workflow" not in st.session_state:
    st.session_state.workflow = ColdMailWorkflow()
if "generated_emails" not in st.session_state:
    st.session_state.generated_emails = None
if "show_approval" not in st.session_state:
    st.session_state.show_approval = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "send_done" not in st.session_state:
    st.session_state.send_done = False


# ─── Page Config ───
st.set_page_config(page_title="ColdMail AI Pro", page_icon="📧", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 2.5rem; font-weight: 700; }
    .subtitle { color: #888; font-size: 1rem; margin-bottom: 2rem; }
    .email-card { background: #1e1e1e; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; }
    .score-badge { background: #2d5a27; color: #90ee90; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📧 ColdMail AI Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">LangGraph Multi-Agent System with MCP Orchestration</div>', unsafe_allow_html=True)


# ─── Sidebar: Profile ───
with st.sidebar:
    st.header("👤 Your Profile")
    
    name = st.text_input("Full Name", value="Kavya Gupta")
    email = st.text_input("Your Email", value="kavya.23bai10538@vitbhopal.ac.in")
    phone = st.text_input("Phone", value="9829803323")
    linkedin = st.text_input("LinkedIn URL", value="https://www.linkedin.com/in/its-kavya")
    github = st.text_input("GitHub URL", value="https://github.com/kavya1b1")
    portfolio = st.text_input("Portfolio URL", value="https://portfolio-neww-rouge.vercel.app")
    college = st.text_input("College", value="VIT BHOPAL")
    degree = st.text_input("Degree", value="B.Tech")
    grad_year = st.number_input("Graduation Year", min_value=2020, max_value=2035, value=2027)
    skills = st.text_area("Skills (comma-separated)", value="html, css, js, python, cpp, ml, rag, ai, fine tuning, llm, nlp, cv, deep learning, artificial neural networking")
    objective = st.text_area("Your Objective", value="intelligence and machine learning and my interests are in python developer, ai developer, ml developer, ai engineer etc")
    tone = st.selectbox("Tone", ["professional", "confident", "humble", "enthusiastic"], index=1)
    
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    resume_path = None
    if resume_file:
        resume_path = f"/tmp/{resume_file.name}"
        with open(resume_path, "wb") as f:
            f.write(resume_file.getvalue())
        st.success(f"📄 {resume_file.name}")
    
    if st.button("💾 Save Profile", use_container_width=True):
        st.success("Profile saved!")


# ─── Main: Campaign Setup ───
st.markdown("## 🎯 Campaign Setup")

col1, col2 = st.columns(2)

with col1:
    goal = st.selectbox("Campaign Goal", ["internship", "full_time", "referral"], index=1, format_func=lambda x: x.replace("_", " ").title())
    mode = st.selectbox("Mode", ["Generate & Send (Manual Approve)", "Generate Only", "Auto Send"])

with col2:
    recipient_input = st.text_area(
        "Recipient Emails (one per line)",
        value="kavya1b1@gmail.com\nguptaggaming@gmail.com\ncareers@evolvexinnovations.org",
        height=120
    )
    recipient_emails = [e.strip() for e in recipient_input.split("\n") if e.strip() and "@" in e.strip()]
    st.info(f"📋 {len(recipient_emails)} recipient(s) ready")


# ─── Helper: Get display name from email ───
import re
def get_display_name(email: str) -> str:
    """Extract a human-readable name from email for labels."""
    if "@" not in email:
        return email
    prefix, domain = email.split("@")
    personal_domains = {
        "gmail.com","yahoo.com","yahoo.in","yahoo.co.in","hotmail.com","outlook.com",
        "live.com","icloud.com","me.com","mac.com","protonmail.com","zoho.com",
        "aol.com","mail.com","yandex.com","qq.com",
    }
    if domain.lower() in personal_domains:
        cleaned = re.sub(r"[0-9._\-]+"," ",prefix).strip()
        words=[w.capitalize() for w in cleaned.split() if len(w)>1]
        return " ".join(words) if words else prefix.capitalize()
    name_part=domain.replace(".com","").replace(".co","").replace(".in","").replace(".org","").replace(".ai","")
    return name_part.split(".")[-1].capitalize()


st.divider()


# ─── Target Roles & Job Descriptions ───
st.markdown("### 📝 Target Roles & Job Descriptions")
st.caption("Specify the role and paste/upload the job description for each recipient")

roles = []
job_descriptions = []

cols = st.columns(min(len(recipient_emails), 3))
for i, rec_email in enumerate(recipient_emails):
    with cols[i % len(cols)]:
        display_name = get_display_name(rec_email)

        role = st.text_input(
            f"Role for {display_name}",
            key=f"role_input_{i}",
            placeholder="e.g., Software Engineer"
        )
        roles.append(role)

        with st.expander(f"📄 Job Description for {display_name}", expanded=False):
            jd_text = st.text_area(
                "Paste JD text",
                key=f"jd_text_{i}",
                height=120,
                placeholder="Paste the job description here..."
            )

            jd_pdf = st.file_uploader(
                "Or upload JD PDF",
                type=["pdf"],
                key=f"jd_pdf_{i}"
            )

            if jd_pdf:
                extracted = extract_text_from_pdf(jd_pdf)
                if not extracted.startswith("[Error"):
                    jd_text = extracted
                    st.success(f"Extracted {len(extracted)} characters from PDF")
                else:
                    st.error(extracted)

            job_descriptions.append(jd_text)


# ─── Generate Button ───
if st.button("✨ Generate Personalized Emails", type="primary", use_container_width=True):
    if not recipient_emails:
        st.error("Please enter at least one recipient email.")
    else:
        with st.spinner("🤖 LangGraph Agents working: Research → Match → Write → Review..."):
            try:
                # Build profile
                profile = UserProfile(
                    name=name,
                    email=email,
                    phone=phone or None,
                    linkedin=linkedin or None,
                    github=github or None,
                    portfolio=portfolio or None,
                    resume_path=resume_path,
                    college=college,
                    degree=degree,
                    graduation_year=int(grad_year),
                    skills=[s.strip() for s in skills.split(",") if s.strip()],
                    objective=objective,
                    tone=Tone(tone),
                )
                
                # Build initial state
                thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state.thread_id = thread_id
                
                initial_state = {
                    "user_profile": profile,
                    "recipient_emails": recipient_emails,
                    "goal": CampaignGoal(goal),
                    "roles": roles,
                    "job_descriptions": job_descriptions,
                    "parsed_jobs": [],
                    "companies": [],
                    "matches": [],
                    "generated_emails": [],
                    "reviews": [],
                    "needs_rewrite": [],
                    "rewrite_attempts": 0,
                    "approved_indices": [],
                    "awaiting_approval": False,
                    "email_reviewed": False,
                    "email_written": False,
                    "matched": False,
                    "company_researched": False,
                    "errors": [],
                    "logs": [],
                    "session_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Run workflow (pauses at human_approval)
                result = st.session_state.workflow.run(initial_state, thread_id=thread_id)
                
                emails = result.values.get("generated_emails", [])
                if emails:
                    st.session_state.generated_emails = emails
                    st.session_state.show_approval = True
                    st.session_state.send_done = False
                    st.success(f"Generated {len(emails)} personalized emails!")
                    st.rerun()
                else:
                    st.error("No emails were generated. Check the logs.")
                    
            except Exception as e:
                logger.error(f"Workflow error: {e}", exc_info=True)
                st.error(f"Error: {str(e)}")


# ─── Review & Approve Section ───
if st.session_state.show_approval and st.session_state.generated_emails:
    st.divider()
    st.markdown("## 📋 Review & Approve")
    
    emails = st.session_state.generated_emails
    approved_indices = []
    
    for i, email in enumerate(emails):
        email_data = email if isinstance(email, dict) else email.model_dump()
        
        with st.container():
            col_left, col_right = st.columns([4, 1])
            
            with col_left:
                st.markdown(f"**To:** `{email_data['recipient_email']}`")
                st.markdown(f"**Company/Contact:** {email_data['company_name']}")
                if email_data.get("role"):
                    st.markdown(f"**Target Role:** {email_data['role']}")
                
                # Role editor
                current_role = email_data.get("role", roles[i] if i < len(roles) else "")
                new_role = st.text_input(
                    "Role / Position",
                    value=current_role,
                    key=f"role_edit_{i}",
                    placeholder="e.g., Software Engineer"
                )
                if new_role:
                    email_data["role"] = new_role
                    # Update subject if role changed
                    if email_data.get("company_name") and "Application for" in email_data.get("subject", ""):
                        email_data["subject"] = f"Application for {new_role} at {email_data['company_name']} — {name}"
                
                st.markdown(f"**Subject:** {email_data['subject']}")
                
                with st.expander("📄 View Full Email"):
                    st.text_area("Email Body", value=email_data['body'], height=300, key=f"body_{i}", disabled=True)
                    if email_data.get("resume_attached"):
                        st.info("📎 Resume will be attached when sending")
                
                if email_data.get("key_points_used"):
                    st.caption(f"🎯 Personalization: {', '.join(email_data['key_points_used'])}")
            
            with col_right:
                score = email_data.get("personalization_score", 0)
                st.markdown(f'<div class="score-badge">⭐ {score}/100</div>', unsafe_allow_html=True)
                
                approved = st.toggle(
                    "✅ Approve for sending",
                    key=f"approve_{i}",
                    value=False
                )
                if approved:
                    approved_indices.append(i)
            
            st.divider()
    
    st.session_state.approved_indices = approved_indices
    
    # Send button
    if st.button("🚀 Send Approved Emails", type="primary", use_container_width=True):
        if not approved_indices:
            st.warning("Please approve at least one email.")
        else:
            with st.spinner("📤 Sending approved emails..."):
                try:
                    workflow = st.session_state.workflow
                    thread_id = st.session_state.thread_id
                    config = {"configurable": {"thread_id": thread_id}}
                    
                    # Update state with user approvals and edited roles
                    updated_emails = []
                    for i, email in enumerate(emails):
                        email_data = email if isinstance(email, dict) else email.model_dump()
                        if i < len(roles) and roles[i]:
                            email_data["role"] = roles[i]
                        updated_emails.append(email_data)
                    
                    update_values = {
                        "generated_emails": updated_emails,
                        "approved_indices": approved_indices,
                        "awaiting_approval": False,
                    }
                    
                    workflow.graph.update_state(config, update_values)
                    
                    # Resume workflow from human_approval
                    for event in workflow.graph.stream(None, config):
                        if "__end__" not in event:
                            logger.info(f"Send event: {list(event.keys())}")
                    
                    # Get final state
                    final_state = workflow.graph.get_state(config)
                    send_results = final_state.values.get("send_results", {})
                    
                    sent = send_results.get("sent", 0)
                    failed = send_results.get("failed", 0)
                    
                    st.session_state.send_done = True
                    st.success(f"📤 Sent {sent} emails! {f'({failed} failed)' if failed else ''}")
                    st.balloons()
                    
                except Exception as e:
                    logger.error(f"Send error: {e}", exc_info=True)
                    st.error(f"Send failed: {str(e)}")


# ─── Reset ───
if st.session_state.send_done:
    if st.button("🔄 Start New Campaign", use_container_width=True):
        for key in ["generated_emails", "show_approval", "thread_id", "send_done", "approved_indices"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()