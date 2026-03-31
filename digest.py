"""
Daily digest — emails Jackson a morning summary of leads to follow up with.
Runs via GitHub Actions every day at 9 AM Mountain Time.
"""

import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from dotenv import load_dotenv

import sheets

load_dotenv()

SKIP_STATUSES = {'not_interested', 'Not Interested', 'Closed', 'closed'}


def send_digest():
    today = date.today().strftime('%A, %B %-d')

    # ── Gather leads that need follow-up ──────────────────────────────────────
    try:
        leads = sheets.get_all_leads()
    except Exception as e:
        print(f"[digest] ERROR reading leads: {e}")
        leads = []

    try:
        customers = sheets.get_all_customers()
    except Exception as e:
        print(f"[digest] ERROR reading customers: {e}")
        customers = []

    followup_leads = [
        l for l in leads
        if l.get('Status', '') not in SKIP_STATUSES
    ]

    followup_customers = [
        c for c in customers
        if c.get('Status', '') not in SKIP_STATUSES
    ]

    total = len(followup_leads) + len(followup_customers)

    if total == 0:
        print("[digest] No contacts to follow up with today — skipping email.")
        return

    # ── Build email body ───────────────────────────────────────────────────────
    lines = [
        f"Hey Jackson, here's your follow-up list for {today}.\n",
        f"You've got {total} contact{'s' if total != 1 else ''} to stay on top of.\n",
    ]

    if followup_leads:
        lines.append(f"\n── WARM LEADS ({len(followup_leads)}) ──────────────────────\n")
        for l in followup_leads:
            name    = f"{l.get('First Name', '')} {l.get('Last Name', '')}".strip()
            phone   = l.get('Phone', 'No phone')
            address = l.get('Address', '')
            status  = l.get('Status', '')
            last    = l.get('Last Contacted', '')
            notes   = l.get('Notes', '')

            lines.append(f"{name}")
            lines.append(f"  Phone:   {phone}")
            if address:
                lines.append(f"  Address: {address}")
            lines.append(f"  Status:  {status}")
            if last:
                lines.append(f"  Last contacted: {last}")
            if notes:
                lines.append(f"  Notes:   {notes}")
            lines.append("")

    if followup_customers:
        lines.append(f"\n── CURRENT CUSTOMERS ({len(followup_customers)}) ─────────────\n")
        for c in followup_customers:
            name    = f"{c.get('First Name', '')} {c.get('Last Name', '')}".strip()
            phone   = c.get('Phone', 'No phone')
            address = c.get('Address', '')
            referrals = c.get('Referral Count', 0)
            notes   = c.get('Notes', '')

            lines.append(f"{name}")
            lines.append(f"  Phone:   {phone}")
            if address:
                lines.append(f"  Address: {address}")
            lines.append(f"  Referrals given: {referrals}")
            if notes:
                lines.append(f"  Notes:   {notes}")
            lines.append("")

    lines.append("\nGo get em — Jackson")

    body = "\n".join(lines)

    # ── Send email ─────────────────────────────────────────────────────────────
    gmail_address  = os.environ['GMAIL_ADDRESS']
    gmail_password = os.environ['GMAIL_APP_PASSWORD']
    owner_email    = os.environ['OWNER_EMAIL']

    msg = MIMEText(body)
    msg['Subject'] = f"Follow-up list for {today} ({total} contact{'s' if total != 1 else ''})"
    msg['From']    = f"Jackson (BrightSpeed) <{gmail_address}>"
    msg['To']      = owner_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, owner_email, msg.as_string())

    print(f"[digest] Sent follow-up digest to {owner_email} ({total} contacts)")


if __name__ == '__main__':
    send_digest()
