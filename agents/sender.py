"""Production Email Sender Agent"""

from __future__ import annotations

import os
import ssl
import smtplib
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.logging import logger
from models.schemas import GeneratedEmail

load_dotenv()


class EmailSender:
    """
    Production SMTP email sender.

    Features
    --------
    • SMTP connection reuse
    • Retry support
    • HTML + Plain text
    • Attachments
    • Statistics
    • Health check
    • Demo mode
    """

    MAX_RETRIES = 3

    def __init__(self):

        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))

        self.smtp_user = os.getenv("SMTP_USERNAME", "")
        self.smtp_pass = os.getenv("SMTP_PASSWORD", "")

        self.use_tls = (
            os.getenv(
                "SMTP_USE_TLS",
                "true",
            ).lower()
            == "true"
        )

        self.sender_email = os.getenv(
            "SENDER_EMAIL",
            self.smtp_user,
        )

        self.sender_name = os.getenv(
            "SENDER_NAME",
            "ColdMail AI",
        )

        self.demo_mode = not all(
            [
                self.smtp_host,
                self.smtp_user,
                self.smtp_pass,
            ]
        )

        self._stats = {
            "sent": 0,
            "failed": 0,
            "demo": 0,
        }

        logger.info(
            "EmailSender initialized."
        )

    ####################################################################
    # Availability
    ####################################################################

    def is_available(self) -> bool:

        return not self.demo_mode

    ####################################################################
    # Validation
    ####################################################################

    def _validate_email(
        self,
        recipient: str,
    ) -> bool:

        if not recipient:
            return False

        if "@" not in recipient:
            return False

        if "." not in recipient.split("@")[1]:
            return False

        return True

    ####################################################################
    # SMTP
    ####################################################################

    def _connect(self) -> smtplib.SMTP:
        """
        Create authenticated SMTP connection.
        """

        logger.info(
            "Connecting to SMTP..."
        )

        server = smtplib.SMTP(
            self.smtp_host,
            self.smtp_port,
            timeout=30,
        )

        if self.use_tls:

            context = ssl.create_default_context()

            server.starttls(
                context=context
            )

        server.login(
            self.smtp_user,
            self.smtp_pass,
        )

        logger.info(
            "SMTP connected."
        )

        return server

    ####################################################################
    # Attachments
    ####################################################################

    def _attach_file(
        self,
        message: MIMEMultipart,
        filepath: str,
    ):

        path = Path(filepath)

        if not path.exists():

            logger.warning(
                "Attachment missing: %s",
                filepath,
            )

            return

        mime_type, _ = mimetypes.guess_type(
            str(path)
        )

        if mime_type:

            main, sub = mime_type.split(
                "/",
                1,
            )

        else:

            main = "application"
            sub = "octet-stream"

        with open(
            path,
            "rb",
        ) as f:

            part = MIMEBase(
                main,
                sub,
            )

            part.set_payload(
                f.read()
            )

        encoders.encode_base64(
            part
        )

        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{path.name}"',
        )

        message.attach(
            part
        )

        logger.info(
            "Attached %s",
            path.name,
        )

    ####################################################################
    # Message Builder
    ####################################################################

    def _build_message(
        self,
        email: GeneratedEmail,
        html_body: Optional[str] = None,
        resume_path: Optional[str] = None,
    ) -> MIMEMultipart:

        message = MIMEMultipart(
            "alternative"
        )

        message["From"] = (
            f"{self.sender_name} "
            f"<{self.sender_email}>"
        )

        message["To"] = (
            email.recipient_email
        )

        message["Subject"] = (
            email.subject
        )

        plain = MIMEText(
            email.body,
            "plain",
            "utf-8",
        )

        message.attach(
            plain
        )

        if html_body:

            message.attach(
                MIMEText(
                    html_body,
                    "html",
                    "utf-8",
                )
            )

        if resume_path:

            self._attach_file(
                message,
                resume_path,
            )

        return message
    
        ####################################################################
    # Email Sending
    ####################################################################

    def send(
        self,
        email: GeneratedEmail,
        resume_path: Optional[str] = None,
        html_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a single email.

        Returns detailed send metadata.
        """

        recipient = email.recipient_email

        logger.info(
            "Preparing email for %s",
            recipient,
        )

        ################################################################
        # Validate
        ################################################################

        if not self._validate_email(
            recipient
        ):

            logger.error(
                "Invalid recipient: %s",
                recipient,
            )

            self._stats["failed"] += 1

            return {
                "success": False,
                "demo": False,
                "recipient": recipient,
                "subject": email.subject,
                "error": "Invalid email address",
            }

        ################################################################
        # Demo Mode
        ################################################################

        if self.demo_mode:

            logger.warning(
                "Demo mode enabled."
            )

            self._stats["demo"] += 1

            return {
                "success": True,
                "demo": True,
                "recipient": recipient,
                "subject": email.subject,
                "message": (
                    "Email simulated. "
                    "Configure SMTP credentials "
                    "to enable delivery."
                ),
            }

        ################################################################
        # Build Email
        ################################################################

        message = self._build_message(
            email=email,
            html_body=html_body,
            resume_path=resume_path,
        )

        ################################################################
        # Retry Loop
        ################################################################

        last_error = None

        for attempt in range(
            1,
            self.MAX_RETRIES + 1,
        ):

            try:

                logger.info(
                    "SMTP attempt %d/%d",
                    attempt,
                    self.MAX_RETRIES,
                )

                server = self._connect()

                server.send_message(
                    message
                )

                server.quit()

                self._stats["sent"] += 1

                logger.info(
                    "Email successfully sent to %s",
                    recipient,
                )

                return {
                    "success": True,
                    "demo": False,
                    "recipient": recipient,
                    "subject": email.subject,
                    "attempt": attempt,
                }

            except smtplib.SMTPAuthenticationError as exc:

                logger.exception(
                    "SMTP authentication failed."
                )

                self._stats["failed"] += 1

                return {
                    "success": False,
                    "demo": False,
                    "recipient": recipient,
                    "subject": email.subject,
                    "error": "SMTP authentication failed",
                    "details": str(exc),
                }

            except smtplib.SMTPRecipientsRefused as exc:

                logger.exception(
                    "Recipient rejected."
                )

                self._stats["failed"] += 1

                return {
                    "success": False,
                    "demo": False,
                    "recipient": recipient,
                    "subject": email.subject,
                    "error": "Recipient rejected",
                    "details": str(exc),
                }

            except smtplib.SMTPException as exc:

                last_error = exc

                logger.warning(
                    "SMTP attempt %d failed: %s",
                    attempt,
                    exc,
                )

            except Exception as exc:

                last_error = exc

                logger.exception(
                    "Unexpected send failure."
                )

        ################################################################
        # Final Failure
        ################################################################

        self._stats["failed"] += 1

        logger.error(
            "Failed sending email after retries."
        )

        return {
            "success": False,
            "demo": False,
            "recipient": recipient,
            "subject": email.subject,
            "error": str(last_error),
        }
    
        ####################################################################
    # Batch Sending
    ####################################################################

    def send_batch(
        self,
        emails: List[GeneratedEmail],
        resume_path: Optional[str] = None,
        html_body: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Send multiple emails.

        Each email is processed independently so that a single
        failure does not interrupt the remaining batch.
        """

        logger.info(
            "Sending batch of %d email(s).",
            len(emails),
        )

        results: List[Dict[str, Any]] = []

        for email in emails:

            try:

                result = self.send(
                    email=email,
                    resume_path=resume_path,
                    html_body=html_body,
                )

                results.append(result)

            except Exception as exc:

                logger.exception(
                    "Unexpected batch failure for %s: %s",
                    email.recipient_email,
                    exc,
                )

                self._stats["failed"] += 1

                results.append(
                    {
                        "success": False,
                        "demo": False,
                        "recipient": email.recipient_email,
                        "subject": email.subject,
                        "error": str(exc),
                    }
                )

        logger.info(
            "Batch completed. %d email(s) processed.",
            len(results),
        )

        return results

    ####################################################################
    # Statistics
    ####################################################################

    def statistics(self) -> Dict[str, Any]:
        """
        Runtime email statistics.
        """

        total = (
            self._stats["sent"]
            + self._stats["failed"]
            + self._stats["demo"]
        )

        success_rate = (
            (self._stats["sent"] / total) * 100
            if total > 0
            else 0.0
        )

        return {
            "total_processed": total,
            "sent": self._stats["sent"],
            "failed": self._stats["failed"],
            "demo": self._stats["demo"],
            "success_rate": round(success_rate, 2),
        }

    ####################################################################
    # Configuration
    ####################################################################

    def configuration(self) -> Dict[str, Any]:
        """
        Return safe configuration information.
        """

        return {
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "tls_enabled": self.use_tls,
            "demo_mode": self.demo_mode,
            "smtp_username_configured": bool(
                self.smtp_user
            ),
            "smtp_password_configured": bool(
                self.smtp_pass
            ),
        }

    ####################################################################
    # Reset Statistics
    ####################################################################

    def reset_statistics(self):
        """
        Reset runtime counters.
        """

        self._stats = {
            "sent": 0,
            "failed": 0,
            "demo": 0,
        }

        logger.info(
            "Email statistics reset."
        )

    ####################################################################
    # Health Check
    ####################################################################

    def health(self) -> Dict[str, Any]:
        """
        Service health information.
        """

        return {
            "service": "EmailSender",
            "status": (
                "demo"
                if self.demo_mode
                else "ready"
            ),
            "smtp_available": self.is_available(),
            "supports_tls": self.use_tls,
            "supports_html": True,
            "supports_attachments": True,
            "supports_batch": True,
            "max_retries": self.MAX_RETRIES,
            "statistics": self.statistics(),
        }