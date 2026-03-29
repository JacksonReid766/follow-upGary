"""
Gmail API reader — polls the inbox for inbound SMS replies from T-Mobile's
email-to-SMS gateway. T-Mobile sends replies to your Gmail from addresses
like 6155551234@tmomail.net.

Authentication:
  Run `python auth_setup.py` once locally to generate token.json, then
  store its contents as the GMAIL_TOKEN env var / GitHub Actions secret.
"""

import os
import re
import json
import base64
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
# Filter: messages from tmomail.net that are unread
GMAIL_QUERY = 'from:tmomail.net is:unread'


def _get_service():
    """Build an authenticated Gmail API service."""
    creds = None

    token_json = os.environ.get('GMAIL_TOKEN')
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds:
        raise RuntimeError(
            "No Gmail credentials found. "
            "Run `python auth_setup.py` to generate token.json, "
            "then set GMAIL_TOKEN in your environment."
        )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build('gmail', 'v1', credentials=creds)


def get_unread_sms_replies() -> list[dict]:
    """
    Fetch all unread SMS replies from tmomail.net.

    Returns a list of dicts:
        {
            'message_id': str,   # Gmail message ID (use to mark as read)
            'phone':      str,   # 10-digit sender phone number
            'body':       str,   # plain-text message body
            'timestamp':  str,   # Unix timestamp in milliseconds (str)
        }
    """
    service = _get_service()

    result = service.users().messages().list(
        userId='me',
        q=GMAIL_QUERY,
        maxResults=50,
    ).execute()

    messages = result.get('messages', [])
    if not messages:
        return []

    replies = []
    for msg_stub in messages:
        msg = service.users().messages().get(
            userId='me',
            id=msg_stub['id'],
            format='full',
        ).execute()

        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        from_addr = headers.get('From', '')

        # Extract the 10-digit number from the sender address.
        # T-Mobile sends as: 6155551234@tmomail.net  or  <6155551234@tmomail.net>
        # Some carriers include the country code: 16155551234@tmomail.net
        phone_match = re.search(r'1?(\d{10})@tmomail\.net', from_addr)
        if not phone_match:
            continue  # not a recognizable SMS reply address

        phone = phone_match.group(1)
        body  = _extract_body(msg['payload'])

        # Strip quoted reply text (lines starting with ">") — keep only the new reply
        body = _strip_quoted_text(body)

        if not body:
            continue

        replies.append({
            'message_id': msg['id'],
            'phone':      phone,
            'body':       body,
            'timestamp':  msg['internalDate'],
        })

    return replies


def mark_as_read(message_id: str):
    """Remove the UNREAD label from a Gmail message."""
    service = _get_service()
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']},
    ).execute()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_body(payload: dict) -> str:
    """Recursively walk a Gmail message payload and return the plain-text body."""
    # Leaf node with data
    data = payload.get('body', {}).get('data', '')
    if data:
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace').strip()

    # Prefer text/plain parts
    for part in payload.get('parts', []):
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace').strip()

    # Recurse into any nested parts
    for part in payload.get('parts', []):
        result = _extract_body(part)
        if result:
            return result

    return ''


def _strip_quoted_text(body: str) -> str:
    """
    Remove quoted-reply lines ("> ...") from SMS gateway forwarded messages.
    Keep only the first non-empty, non-quoted block.
    """
    lines = body.splitlines()
    clean = []
    for line in lines:
        if line.startswith('>'):
            break  # quoted text starts — discard everything from here
        clean.append(line)
    return '\n'.join(clean).strip()
