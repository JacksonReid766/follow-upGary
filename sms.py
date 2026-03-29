"""
SMS helper — sends outbound texts via the T-Mobile email-to-SMS gateway.

T-Mobile gateway: {10-digit-number}@tmomail.net
Messages arrive as plain text on the recipient's phone.
Replies come back to your Gmail inbox from {number}@tmomail.net.
"""

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()


def send_sms(to_phone: str, message: str):
    """
    Send an SMS to a T-Mobile number via Gmail SMTP.

    Args:
        to_phone: 10-digit number (dashes/spaces are stripped automatically)
        message:  Plain text body. Keep under 160 chars to avoid splitting.
    """
    gmail_address  = os.environ['GMAIL_ADDRESS']
    gmail_password = os.environ['GMAIL_APP_PASSWORD']

    # Normalize phone — strip anything that isn't a digit
    digits = ''.join(c for c in str(to_phone) if c.isdigit())
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]  # strip leading country code
    if len(digits) != 10:
        raise ValueError(f"send_sms: expected 10-digit number, got '{to_phone}'")

    to_email = f"{digits}@tmomail.net"

    msg = MIMEText(message)
    msg['From']    = gmail_address
    msg['To']      = to_email
    msg['Subject'] = ''  # subject shows as body prefix on some carriers — keep blank

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_address, gmail_password)
        server.send_message(msg)

    print(f"[sms] Sent to {digits}: {message[:60]}{'...' if len(message) > 60 else ''}")
