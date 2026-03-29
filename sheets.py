"""
Google Sheets helper — shared by all agents.

Sheet columns (must match Code.gs exactly):
  Warm Leads:  Timestamp | First Name | Last Name | Phone | Address | Notes | Referred By | Status | Last Contacted
  Customers:   Timestamp | First Name | Last Name | Phone | Address | Notes | Status | Referral Count
"""

import os
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SHEET_ID = os.environ['GOOGLE_SHEET_ID']
WARM_LEADS_TAB = 'Warm Leads'
CUSTOMERS_TAB  = 'Customers'

# 1-based column positions matching Code.gs headers
LEAD_COLS = {
    'timestamp':      1,
    'first_name':     2,
    'last_name':      3,
    'phone':          4,
    'address':        5,
    'notes':          6,
    'referred_by':    7,
    'status':         8,
    'last_contacted': 9,
}
CUSTOMER_COLS = {
    'timestamp':      1,
    'first_name':     2,
    'last_name':      3,
    'phone':          4,
    'address':        5,
    'notes':          6,
    'status':         7,
    'referral_count': 8,
}


def _get_client():
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # Fallback to local file for development
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    return gspread.authorize(creds)


def _normalize_phone(phone: str) -> str:
    return str(phone).replace('-', '').replace(' ', '').replace('+1', '').strip()


# ── Reads ──────────────────────────────────────────────────────────────────────

def get_all_leads() -> list[dict]:
    """Return all rows from Warm Leads as a list of dicts, with '_row' (1-indexed sheet row)."""
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet(WARM_LEADS_TAB)
    records = ws.get_all_records()
    for i, r in enumerate(records):
        r['_row'] = i + 2  # row 1 is the header
    return records


def get_all_customers() -> list[dict]:
    """Return all rows from Customers as a list of dicts, with '_row'."""
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet(CUSTOMERS_TAB)
    records = ws.get_all_records()
    for i, r in enumerate(records):
        r['_row'] = i + 2
    return records


def find_contact_by_phone(phone: str) -> tuple[dict | None, str | None]:
    """
    Search both sheets for a contact matching the given phone number.
    Returns (contact_dict, 'lead'|'customer') or (None, None) if not found.
    """
    target = _normalize_phone(phone)

    for lead in get_all_leads():
        if _normalize_phone(str(lead.get('Phone', ''))) == target:
            return lead, 'lead'

    for customer in get_all_customers():
        if _normalize_phone(str(customer.get('Phone', ''))) == target:
            return customer, 'customer'

    return None, None


# ── Writes ─────────────────────────────────────────────────────────────────────

def update_lead(row: int, **kwargs):
    """
    Update specific columns for a lead row.
    Valid kwargs: status, last_contacted, notes, referred_by
    """
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet(WARM_LEADS_TAB)
    col_map = {
        'notes':          LEAD_COLS['notes'],
        'referred_by':    LEAD_COLS['referred_by'],
        'status':         LEAD_COLS['status'],
        'last_contacted': LEAD_COLS['last_contacted'],
    }
    for key, val in kwargs.items():
        if key in col_map:
            ws.update_cell(row, col_map[key], val)


def update_customer(row: int, **kwargs):
    """
    Update specific columns for a customer row.
    Valid kwargs: status, notes, referral_count
    """
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet(CUSTOMERS_TAB)
    col_map = {
        'notes':          CUSTOMER_COLS['notes'],
        'status':         CUSTOMER_COLS['status'],
        'referral_count': CUSTOMER_COLS['referral_count'],
    }
    for key, val in kwargs.items():
        if key in col_map:
            ws.update_cell(row, col_map[key], val)


def increment_referral_count(customer: dict):
    """Add 1 to a customer's Referral Count."""
    current = int(customer.get('Referral Count', 0) or 0)
    update_customer(customer['_row'], referral_count=current + 1)


def add_referral_lead(first: str, last: str, phone: str, referred_by: str, notes: str = ''):
    """Append a new row to Warm Leads (called when a customer gives a referral)."""
    client = _get_client()
    ws = client.open_by_key(SHEET_ID).worksheet(WARM_LEADS_TAB)
    ws.append_row([
        datetime.utcnow().isoformat(),
        first,
        last,
        _normalize_phone(phone),
        '',       # address — unknown
        notes,
        referred_by,
        'New',    # status
        '',       # last contacted
    ])


# ── Helpers ───────────────────────────────────────────────────────────────────

def append_note(existing: str, new_note: str) -> str:
    """Prepend a timestamped note to existing notes."""
    existing = (existing or '').strip()
    return f"{existing}\n{new_note}".strip()
