"""
Monthly scheduler — intended to run on the last Friday of every month via GitHub Actions.

For each active contact in the sheet, it asks Claude whether now is the right
time to reach out (based on notes + timing hints), then triggers the appropriate
agent for those that get a green light.

Usage:
    python scheduler.py            # only runs on the last Friday of the month
    python scheduler.py --force    # run regardless of date (for testing)
"""

import os
import sys
from datetime import date, timedelta
import anthropic
from dotenv import load_dotenv

import sheets
import referral_agent
import warm_lead_agent

load_dotenv()

MODEL = 'claude-sonnet-4-20250514'


# ── Date logic ─────────────────────────────────────────────────────────────────

def is_last_friday_of_month(d: date | None = None) -> bool:
    """Return True if `d` (default: today) is the last Friday of its month."""
    if d is None:
        d = date.today()
    if d.weekday() != 4:  # 4 = Friday
        return False
    next_friday = d + timedelta(weeks=1)
    return next_friday.month != d.month


# ── Claude timing check ────────────────────────────────────────────────────────

def _should_reach_out(contact_type: str, contact: dict) -> bool:
    """
    Ask Claude whether now is a good time to reach out to this contact.
    Uses the Notes field for timing context (e.g. "call back in March").
    """
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    first = contact.get('First Name', '')
    last  = contact.get('Last Name', '')
    name  = f"{first} {last}".strip() or 'Unknown'
    notes          = contact.get('Notes', '') or 'No notes.'
    status         = contact.get('Status', '') or 'Unknown'
    last_contacted = contact.get('Last Contacted', '') or 'Never'
    today_str      = date.today().strftime('%B %d, %Y')

    prompt = f"""\
You help schedule SMS outreach for a fiber internet door-to-door sales operation.

Today: {today_str}
Contact type: {contact_type}
Name: {name}
Status: {status}
Last contacted: {last_contacted}
Notes: {notes}

Should we text this {contact_type} today? Consider:
- Explicit timing hints in the notes ("call back in March", "contract ends Q2", "try again in 3 months")
- How recently they were last contacted (avoid texting again too soon — give at least 3 weeks)
- Whether their status suggests they're worth pursuing (don't reach out to Archived leads)
- For customers: whether they seem like good referral candidates based on the notes

Reply with exactly:
YES - [one sentence reason]
  or
NO  - [one sentence reason]\
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=80,
        messages=[{'role': 'user', 'content': prompt}],
    )

    answer = response.content[0].text.strip()
    decision = answer.upper().startswith('YES')
    print(f"    Claude: {answer[:100]}")
    return decision


# ── Main ──────────────────────────────────────────────────────────────────────

def run(force: bool = False):
    today = date.today()

    if not force and not is_last_friday_of_month(today):
        print(
            f"[scheduler] Today is {today} ({today.strftime('%A')}) — "
            f"not the last Friday of the month. Pass --force to run anyway."
        )
        return

    print(f"[scheduler] Running monthly outreach for {today.strftime('%B %Y')}...")
    sent = 0

    # ── Customers → referral agent ────────────────────────────────────────────
    print("\n[scheduler] Checking customers for referral outreach...")
    try:
        customers = sheets.get_all_customers()
    except Exception as e:
        print(f"  ERROR reading customers sheet: {e}")
        customers = []

    for customer in customers:
        if customer.get('Status', '') != 'Active':
            continue
        name = f"{customer.get('First Name', '')} {customer.get('Last Name', '')}".strip()
        phone = customer.get('Phone', '')
        print(f"  Checking {name} ({phone})...")
        try:
            if _should_reach_out('customer', customer):
                referral_agent.send_referral_outreach(customer)
                sent += 1
            else:
                print(f"    → Skipping {name}")
        except Exception as e:
            print(f"    ERROR reaching out to {name}: {e}")

    # ── Warm leads → lead agent ───────────────────────────────────────────────
    print("\n[scheduler] Checking warm leads for outreach...")
    try:
        leads = sheets.get_all_leads()
    except Exception as e:
        print(f"  ERROR reading leads sheet: {e}")
        leads = []

    for lead in leads:
        status = lead.get('Status', '')
        if status in ('Archived', 'Closed', 'Booked'):
            continue
        name = f"{lead.get('First Name', '')} {lead.get('Last Name', '')}".strip()
        phone = lead.get('Phone', '')
        print(f"  Checking {name} ({phone})...")
        try:
            if _should_reach_out('warm lead', lead):
                warm_lead_agent.send_lead_outreach(lead)
                sent += 1
            else:
                print(f"    → Skipping {name}")
        except Exception as e:
            print(f"    ERROR reaching out to {name}: {e}")

    print(f"\n[scheduler] Done. Sent {sent} outreach message(s).")


if __name__ == '__main__':
    force = '--force' in sys.argv
    run(force=force)
