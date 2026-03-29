"""
Owner notification helper — sends email alerts when something important happens:
  • A warm lead books (or expresses interest in) a closing call
  • A customer provides a new referral
"""

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()


def _send_email(subject: str, body: str):
    gmail_address  = os.environ.get('GMAIL_ADDRESS', '')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '')
    owner_email    = os.environ.get('OWNER_EMAIL', '')

    if not all([gmail_address, gmail_password, owner_email]):
        # Graceful no-op in dev when env vars aren't set
        print(f"[notify] (no credentials) Would send: {subject}")
        return

    msg = MIMEMultipart()
    msg['From']    = gmail_address
    msg['To']      = owner_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_address, gmail_password)
        server.send_message(msg)

    print(f"[notify] Email sent → {owner_email}: {subject}")


def notify_closing_call_booked(lead_name: str, phone: str, context: str = ''):
    """Alert the owner that a warm lead wants to move forward."""
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    subject = f"Closing call booked — {lead_name}"
    body = (
        f"A warm lead is ready to move forward!\n\n"
        f"Lead:    {lead_name}\n"
        f"Phone:   {phone}\n"
        f"Time:    {now}\n"
        f"\nWhat they said:\n{context}\n"
        f"\nCall them to confirm details and close the deal."
    )
    _send_email(subject, body)


def notify_new_referral(
    referral_name: str,
    referral_phone: str,
    customer_name: str,
    customer_phone: str,
):
    """Alert the owner that a customer provided a referral."""
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    subject = f"New referral from {customer_name} — {referral_name}"
    body = (
        f"A customer just gave you a referral!\n\n"
        f"Referred by:    {customer_name} ({customer_phone})\n"
        f"Referral name:  {referral_name}\n"
        f"Referral phone: {referral_phone}\n"
        f"Time:           {now}\n"
        f"\nThis contact has been added to your Warm Leads sheet automatically.\n"
        f"Reach out to them — {customer_name} earns $50 when they sign up."
    )
    _send_email(subject, body)
