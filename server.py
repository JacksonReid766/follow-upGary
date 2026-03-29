#!/usr/bin/env python3
"""
Local server for the follow-upGary form.
Run with: python3 server.py
Then open: http://localhost:8080
"""

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from sms import send_sms

PORT = 8080

IMMEDIATE_SMS = """\
Hey {first_name}, this is Jackson with BrightSpeed Fiber! \
Great meeting you today. Feel free to reach me here anytime — I'll be in touch soon!\
"""


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress default access logs

    def do_GET(self):
        html = Path('index.html').read_text()
        # Inject a flag so the form knows it's running locally
        html = html.replace(
            'const SCRIPT_URL',
            'const IS_LOCAL = true;\n  const SCRIPT_URL'
        )
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))

        phone = str(body.get('phone', ''))
        first_name = body.get('firstName', 'there')

        result = {'success': False, 'error': 'Unknown error'}

        if not phone or len(phone) != 10:
            result = {'success': False, 'error': 'Invalid phone number'}
        else:
            try:
                message = IMMEDIATE_SMS.format(first_name=first_name)
                send_sms(phone, message)
                print(f"[server] Immediate SMS sent to {first_name} ({phone})")
                result = {'success': True}
            except Exception as e:
                print(f"[server] SMS failed: {e}")
                result = {'success': False, 'error': str(e)}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    server = HTTPServer(('localhost', PORT), Handler)
    url = f'http://localhost:{PORT}'
    print(f'[server] Running at {url}')
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[server] Stopped.')


if __name__ == '__main__':
    main()
