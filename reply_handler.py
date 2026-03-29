"""
Reply handler — polls Gmail for inbound SMS replies and routes each one to
the correct agent based on which sheet the sender's phone number appears in.

Run via GitHub Actions on a schedule, or locally:
    python reply_handler.py

Routing:
    Phone found in Customers tab → referral_agent.handle_reply()
    Phone found in Warm Leads tab → warm_lead_agent.handle_reply()
    Phone not found → log and skip
"""

import sys
from dotenv import load_dotenv

import sheets
from gmail_reader import get_unread_sms_replies, mark_as_read
import referral_agent
import warm_lead_agent

load_dotenv()


def process_replies():
    print("[reply_handler] Polling Gmail for SMS replies...")

    try:
        replies = get_unread_sms_replies()
    except Exception as e:
        print(f"[reply_handler] ERROR fetching Gmail messages: {e}")
        sys.exit(1)

    if not replies:
        print("[reply_handler] No unread replies.")
        return

    print(f"[reply_handler] Found {len(replies)} unread reply(s).")

    for reply in replies:
        phone   = reply['phone']
        body    = reply['body']
        msg_id  = reply['message_id']

        print(f"\n[reply_handler] From {phone}: {body[:80]}{'...' if len(body) > 80 else ''}")

        if not body.strip():
            print("  Empty body — skipping")
            mark_as_read(msg_id)
            continue

        try:
            contact, contact_type = sheets.find_contact_by_phone(phone)
        except Exception as e:
            print(f"  ERROR looking up phone in sheets: {e}")
            mark_as_read(msg_id)
            continue

        if contact is None:
            print(f"  Phone {phone} not found in either sheet — skipping")
            mark_as_read(msg_id)
            continue

        name = f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip()

        try:
            if contact_type == 'customer':
                print(f"  → Routing to referral_agent for customer: {name}")
                referral_agent.handle_reply(contact, body)

            elif contact_type == 'lead':
                print(f"  → Routing to warm_lead_agent for lead: {name}")
                warm_lead_agent.handle_reply(contact, body)

        except Exception as e:
            print(f"  ERROR in agent handler: {e}")
            # Still mark as read so we don't re-process on next run
        finally:
            mark_as_read(msg_id)

    print("\n[reply_handler] Done.")


if __name__ == '__main__':
    process_replies()
