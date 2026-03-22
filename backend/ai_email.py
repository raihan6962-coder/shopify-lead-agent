import requests
import os
import json

def send_email(to: str, subject: str, body: str):
    apps_script_url = os.environ.get("https://script.google.com/macros/s/AKfycbxyPB4XQx5mX63qQMBJHjbDlk3vBChoSW06Bkp0bDT9kFHCxAQPouD2RXULWizqLXi2xw/exec")
    try:
        response = requests.post(
            apps_script_url,
            data=json.dumps({
                "action":  "send_email",
                "to":      to,
                "subject": subject,
                "body":    body
            }),
            headers={"Content-Type": "application/json"},
            allow_redirects=True,
            timeout=30
        )
        print(f"Email result: {response.text}")
    except Exception as e:
        print(f"Email send error: {e}")
