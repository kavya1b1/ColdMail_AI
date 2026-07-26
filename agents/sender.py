"""Email Sender Agent"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from typing import Dict, Any, List
from models.schemas import GeneratedEmail
from config.logging import logger

load_dotenv()


class EmailSender:
    """Handles sending of generated cold emails via SMTP."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USERNAME", "")      # ← matches your .env
        self.smtp_pass = os.getenv("SMTP_PASSWORD", "")      # ← matches your .env
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_user)
        self.sender_name = os.getenv("SENDER_NAME", "ColdMail AI")
        
        self.demo_mode = not all([self.smtp_host, self.smtp_user, self.smtp_pass])

    def send(self, email: GeneratedEmail, resume_path: str = None) -> Dict[str, Any]:
        """Send a single email."""
        logger.info(f"Sending email to {email.recipient_email}...")
        
        if self.demo_mode:
            logger.warning("DEMO MODE: Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD in .env to send real emails.")
            return {
                "success": True,
                "demo": True,
                "recipient": email.recipient_email,
                "subject": email.subject,
                "message": "Email simulated (demo mode). Configure SMTP in .env to send real emails.",
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = email.recipient_email
            msg["Subject"] = email.subject
            
            msg.attach(MIMEText(email.body, "plain"))
            
            # Attach resume if available
            if resume_path and os.path.exists(resume_path):
                with open(resume_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(resume_path)}"
                )
                msg.attach(part)
                logger.info(f"Attached resume: {os.path.basename(resume_path)}")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info(f"✅ Email ACTUALLY sent to {email.recipient_email}")
            return {
                "success": True,
                "demo": False,
                "recipient": email.recipient_email,
                "subject": email.subject,
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return {
                "success": False,
                "demo": False,
                "recipient": email.recipient_email,
                "error": str(e),
            }

    def send_batch(self, emails: List[GeneratedEmail], resume_path: str = None) -> List[Dict[str, Any]]:
        return [self.send(e, resume_path) for e in emails]