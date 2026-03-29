"""
Referral agent — reaches out to current customers about the $50 referral bonus,
handles their replies, extracts referred name + number, and notifies the owner.

Outbound flow:  scheduler.py → send_referral_outreach(customer)
Inbound flow:   reply_handler.py → handle_reply(customer, reply_text)
"""

import os
from datetime import date
import anthropic
from dotenv import load_dotenv

import sheets
from sms import send_sms
from notify import notify_new_referral

load_dotenv()

MODEL = 'claude-sonnet-4-20250514'

INITIAL_MESSAGE = """\
Hey {first_name}! This is Jackson with BrightSpeed Fiber. Hope the connection's been solid!

Quick heads up — we have a $50 referral bonus running right now. If you know anyone who'd want BrightSpeed Fiber, just reply with their name and number and I'll handle the rest. You get $50 when they sign up!\
"""


# ── Outbound ──────────────────────────────────────────────────────────────────

def send_referral_outreach(customer: dict):
    """Send the initial referral pitch to a customer."""
    first_name = customer.get('First Name', 'there')
    phone = str(customer.get('Phone', ''))

    if not phone:
        print(f"[referral] No phone for customer {first_name} — skipping")
        return

    message = INITIAL_MESSAGE.format(first_name=first_name)
    send_sms(phone, message)

    today = date.today().isoformat()
    sheets.update_customer(
        customer['_row'],
        notes=sheets.append_note(
            customer.get('Notes', ''),
            f"[{today}] Sent referral outreach",
        ),
    )
    print(f"[referral] Outreach sent to {first_name} ({phone})")


# ── Inbound ───────────────────────────────────────────────────────────────────

def handle_reply(customer: dict, reply_text: str) -> str | None:
    """
    Process an inbound reply from a customer.
    Uses Claude with tool use to:
      1. Collect referral details if provided
      2. Answer questions about the program
      3. Gracefully close if not interested
    Returns the text sent back to the customer, or None.
    """
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    first_name = customer.get('First Name', 'there')
    phone      = str(customer.get('Phone', ''))
    notes      = customer.get('Notes', '') or ''
    today      = date.today().isoformat()

    tools = [
        {
            'name': 'collect_referral',
            'description': (
                'Call this when the customer provides a name and phone number for '
                'someone they want to refer. Extract the referral details precisely.'
            ),
            'input_schema': {
                'type': 'object',
                'properties': {
                    'referral_first_name': {
                        'type': 'string',
                        'description': "First name of the person being referred",
                    },
                    'referral_last_name': {
                        'type': 'string',
                        'description': "Last name of the person being referred (empty string if not given)",
                    },
                    'referral_phone': {
                        'type': 'string',
                        'description': "10-digit phone number of the person being referred",
                    },
                },
                'required': ['referral_first_name', 'referral_last_name', 'referral_phone'],
            },
        },
        {
            'name': 'send_reply',
            'description': 'Send a text message reply to the customer.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'description': (
                            'The SMS text to send. Keep it conversational and under 200 characters. '
                            'Do not include any prefixes like "Jackson:" or "Reply:".'
                        ),
                    },
                },
                'required': ['message'],
            },
        },
    ]

    system = f"""\
You are a friendly assistant helping Jackson run a BrightSpeed Fiber referral program via text message.

Customer name: {first_name}
Conversation history / notes: {notes or 'No prior history.'}

Referral program details:
- Customers get $50 when a friend they refer signs up for BrightSpeed Fiber
- Service starts at $49/mo, no contracts, free installation
- Jackson handles all the sales — the customer just needs to give a name and number

Instructions:
- If the customer provided a referral name and phone number, call collect_referral with those details
- If they have questions, answer them briefly and invite them to share a referral
- If they're not interested, be gracious and let them off the hook (no pressure)
- Always call send_reply with a warm, natural response — like a real text, not a marketing message
- If you called collect_referral, confirm in your reply that you've got the info and Jackson will be in touch\
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=system,
        tools=tools,
        messages=[{'role': 'user', 'content': f'Customer replied: "{reply_text}"'}],
    )

    reply_out = None

    # Process all tool calls from Claude's response
    for block in response.content:
        if block.type != 'tool_use':
            continue

        if block.name == 'collect_referral':
            _handle_referral_collected(
                info=block.input,
                customer=customer,
            )

        elif block.name == 'send_reply':
            reply_out = block.input['message']

    # Send the reply and log it
    if reply_out:
        send_sms(phone, reply_out)
        sheets.update_customer(
            customer['_row'],
            notes=sheets.append_note(
                notes,
                f"[{today}] They said: \"{reply_text}\" → Replied: \"{reply_out}\"",
            ),
        )

    return reply_out


# ── Internal ──────────────────────────────────────────────────────────────────

def _handle_referral_collected(info: dict, customer: dict):
    """Add a new referral to Warm Leads and notify the owner."""
    ref_first = info.get('referral_first_name', '').strip()
    ref_last  = info.get('referral_last_name', '').strip()
    ref_phone = ''.join(c for c in str(info.get('referral_phone', '')) if c.isdigit())
    if ref_phone.startswith('1') and len(ref_phone) == 11:
        ref_phone = ref_phone[1:]

    customer_name  = f"{customer.get('First Name', '')} {customer.get('Last Name', '')}".strip()
    customer_phone = str(customer.get('Phone', ''))
    today = date.today().isoformat()

    # Add to Warm Leads sheet
    sheets.add_referral_lead(
        first=ref_first,
        last=ref_last,
        phone=ref_phone,
        referred_by=customer_name,
        notes=f"Referred by {customer_name} on {today}",
    )

    # Increment referral count for this customer
    sheets.increment_referral_count(customer)

    # Email the owner
    notify_new_referral(
        referral_name=f"{ref_first} {ref_last}".strip(),
        referral_phone=ref_phone,
        customer_name=customer_name,
        customer_phone=customer_phone,
    )

    print(f"[referral] New referral added: {ref_first} {ref_last} ({ref_phone}) from {customer_name}")
