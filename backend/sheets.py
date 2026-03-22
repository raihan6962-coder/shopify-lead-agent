import requests
import os

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")

def save_lead(store: dict):
    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json={
                "action": "save_lead",
                "name":    store.get("name", ""),
                "url":     store.get("url", ""),
                "email":   store.get("email", ""),
                "keyword": store.get("keyword", ""),
                "country": store.get("country", ""),
                "status":  store.get("status", ""),
            },
            allow_redirects=True,
            timeout=30
        )
        print(f"Sheet save: {response.text}")
    except Exception as e:
        print(f"Save lead error: {e}")
