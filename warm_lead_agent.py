"""
Warm lead agent — sends outreach texts to warm leads and handles their replies.

Claude classifies each reply into one of five intents and decides how to respond:
  interested    → confirm interest, notify owner to book closing call
  book_call     → lead explicitly wants to talk, notify owner immediately
  question      → answer the question, keep the conversation alive
  maybe_later   → nurture, note their timing, don't push
  not_interested → gracefully close, archive the lead

Outbound flow:  scheduler.py → send_lead_outreach(lead)
Inbound flow:   reply_handler.py → handle_reply(lead, reply_text)
"""

import os
from datetime import date
import anthropic
from dotenv import load_dotenv

import sheets
from sms import send_sms
from notify import notify_closing_call_booked

load_dotenv()

MODEL = 'claude-sonnet-4-20250514'

INITIAL_MESSAGE = """\
Hey {first_name}! This is Jackson with BrightSpeed Fiber — we chatted a while back. \
Just wanted to check in and see if the timing might work better now.

Fast, reliable BrightSpeed Fiber starting at $49/mo, no contracts, free install. \
Happy to answer questions or set up a quick call if you're interested!\
"""

INTENT_VALUES = ['interested', 'book_call', 'question', 'maybe_later', 'not_interested']


# ── Outbound ──────────────────────────────────────────────────────────────────

def send_lead_outreach(lead: dict):
    """Send the initial follow-up text to a warm lead."""
    first_name = lead.get('First Name', 'there')
    phone = str(lead.get('Phone', ''))

    if not phone:
        print(f"[leads] No phone for lead {first_name} — skipping")
        return

    message = INITIAL_MESSAGE.format(first_name=first_name)
    send_sms(phone, message)

    today = date.today().isoformat()
    sheets.update_lead(
        lead['_row'],
        status='Contacted',
        last_contacted=today,
        notes=sheets.append_note(
            lead.get('Notes', ''),
            f"[{today}] Sent initial outreach",
        ),
    )
    print(f"[leads] Outreach sent to {first_name} ({phone})")


# ── Inbound ───────────────────────────────────────────────────────────────────

def handle_reply(lead: dict, reply_text: str) -> str | None:
    """
    Process an inbound reply from a warm lead.
    Claude classifies intent and generates a reply via structured tool use.
    Returns the text sent back to the lead, or None.
    """
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    first_name = lead.get('First Name', 'there')
    last_name  = lead.get('Last Name', '')
    phone      = str(lead.get('Phone', ''))
    notes      = lead.get('Notes', '') or ''
    status     = lead.get('Status', 'Contacted')
    today      = date.today().isoformat()

    tools = [
        {
            'name': 'classify_and_respond',
            'description': (
                'Classify the lead\'s intent and compose a reply. '
                'Always call this tool — it is the only output mechanism.'
            ),
            'input_schema': {
                'type': 'object',
                'properties': {
                    'intent': {
                        'type': 'string',
                        'enum': INTENT_VALUES,
                        'description': (
                            'The lead\'s intent:\n'
                            '  interested     — warm or positive, wants more info\n'
                            '  book_call      — explicitly wants to talk to Jackson / schedule\n'
                            '  question       — has a specific question before deciding\n'
                            '  maybe_later    — timing isn\'t right, open to future contact\n'
                            '  not_interested — clearly doesn\'t want to be contacted again'
                        ),
                    },
                    'response_message': {
                        'type': 'string',
                        'description': (
                            'SMS reply to send. Conversational tone, under 200 characters. '
                            'Do not use Jackson\'s name as a sign-off — keep it natural.'
                        ),
                    },
                    'note': {
                        'type': 'string',
                        'description': 'One-sentence summary of what the lead said (for logging in the sheet).',
                    },
                },
                'required': ['intent', 'response_message', 'note'],
            },
        }
    ]

    system = f"""\
You are a sales assistant texting on behalf of Jackson, a BrightSpeed Fiber internet sales rep. \
You speak in first person as if you are Jackson. You are texting warm leads who have already \
shown interest in switching to fiber internet. Your job is to keep them engaged, answer their \
questions, and move them toward either scheduling a call or rescheduling their install \
appointment, depending on what makes the most sense in context.

If a lead has a general question or hesitation, answer it and push toward a call. \
If a lead was previously scheduled for an install and fell off, push toward rescheduling.

Always be warm, conversational, and concise. These are text messages, not emails. \
Keep responses short, broken into small paragraphs, and easy to read on a phone. \
Never use bullet points or dashes. Use exclamation points sparingly but naturally.

Never quote specific pricing. If asked about price, let them know it depends on their area \
and usage and offer to hop on a quick call to give them an accurate quote.

When you don't know something specific to their address or situation, say so honestly \
and use it as a reason to get them on a call or collect their address.

Lead: {first_name} {last_name}
Current status: {status}
Notes / history: {notes or 'No prior history.'}

FAQ — use these answers as your guide:

Q: How much does it cost?
Pricing depends on their area and what plan fits their usage best. Don't quote a number. \
Offer a quick 5 min call to pull up exactly what's available at their address and give an accurate quote. Ask when's a good time to connect.

Q: What speeds do you offer?
Options for every type of user, from everyday browsing to the fastest tiers. Because it's fiber, \
upload speed matches download — game changer for working from home or video calls. \
The right plan depends on their household. Invite them to a quick call to find the best fit.

Q: Is there a contract?
No long term contract. Month to month, never locked in. \
You'd rather earn their business every month than have them feel trapped.

Q: How long does installation take?
Usually a couple hours or less, up and running same day. \
You work around their schedule. Push to get the appointment on the calendar.

Q: Is my address covered?
Coverage varies street by street since fiber runs on physical lines. \
Ask them to drop their street address so you can pull it up and give a definitive answer.

Q: What's the difference between fiber and my current internet?
Traditional internet runs on copper cable lines built for TV. Fiber is built for data. \
Faster speeds, more stability, no slowdowns during peak hours. Like going from a dirt road to a highway.

Q: I already have internet, why should I switch?
You're not here to say their current service is terrible. \
But most people didn't realize how much it was holding them back until after they switched — \
buffering, dropped calls, slow uploads just go away. Ask what their current setup looks like.

Q: Are there any hidden fees?
No surprises. The price they get is what shows up on the bill. \
Only addition is standard taxes, which apply no matter who they go with.

Q: Can I keep my current email/phone number?
Phone number yes, can port with no issues. Email depends on whether it's tied to their current provider — \
Gmail and similar they keep regardless. Ask what they're currently using.

Q: What if I have a problem after install?
Support is available around the clock. Most issues resolved remotely on the first call.\
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system,
        tools=tools,
        tool_choice={'type': 'tool', 'name': 'classify_and_respond'},
        messages=[{'role': 'user', 'content': f'Lead replied: "{reply_text}"'}],
    )

    for block in response.content:
        if block.type != 'tool_use' or block.name != 'classify_and_respond':
            continue

        intent         = block.input.get('intent', 'question')
        reply_out      = block.input.get('response_message', '')
        note           = block.input.get('note', reply_text[:120])

        # Map intent → sheet status
        new_status = _intent_to_status(intent, status)

        # Update the sheet
        sheets.update_lead(
            lead['_row'],
            status=new_status,
            last_contacted=today,
            notes=sheets.append_note(
                notes,
                f"[{today}] Intent: {intent}. \"{note}\" → Replied: \"{reply_out}\"",
            ),
        )

        # Send the reply
        if reply_out:
            send_sms(phone, reply_out)

        # Notify owner when lead wants to move forward
        if intent in ('book_call', 'interested'):
            notify_closing_call_booked(
                lead_name=f"{first_name} {last_name}".strip(),
                phone=phone,
                context=note,
            )

        print(f"[leads] {first_name}: intent={intent}, status={new_status}")
        return reply_out

    return None


# ── Internal ──────────────────────────────────────────────────────────────────

def _intent_to_status(intent: str, current_status: str) -> str:
    mapping = {
        'book_call':       'Booked',
        'interested':      'Contacted',
        'question':        'Contacted',
        'maybe_later':     'Contacted',
        'not_interested':  'Archived',
    }
    return mapping.get(intent, current_status)
