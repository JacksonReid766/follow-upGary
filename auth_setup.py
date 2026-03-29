"""
One-time Gmail OAuth setup — run this locally to generate token.json,
then add its contents as the GMAIL_TOKEN secret in GitHub Actions.

Prerequisites:
1. Go to console.cloud.google.com
2. Create a project (or use an existing one)
3. Enable the Gmail API: APIs & Services → Library → search "Gmail API" → Enable
4. Create OAuth credentials: APIs & Services → Credentials → Create Credentials
   → OAuth client ID → Desktop app → Download as credentials.json
5. Place credentials.json in this directory
6. Run: python auth_setup.py

After this script runs, copy the printed JSON into your GitHub Actions secret
named GMAIL_TOKEN.
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} not found.")
        print(__doc__)
        return

    print("Opening browser for Gmail authorization...")
    print("Sign in with the Gmail account that will RECEIVE the SMS replies.\n")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        'token':         creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri':     creds.token_uri,
        'client_id':     creds.client_id,
        'client_secret': creds.client_secret,
        'scopes':        list(creds.scopes),
    }

    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f, indent=2)

    print(f"\nSuccess! {TOKEN_FILE} saved.\n")
    print("=" * 60)
    print("Add the following as the GMAIL_TOKEN secret in GitHub Actions")
    print("(Settings → Secrets and variables → Actions → New secret):")
    print("=" * 60)
    print(json.dumps(token_data))
    print("=" * 60)
    print("\nAlso add credentials.json to .gitignore — never commit it.")


if __name__ == '__main__':
    main()
