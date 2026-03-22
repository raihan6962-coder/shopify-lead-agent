from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
import json
import uuid
import requests
from bs4 import BeautifulSoup
import re
import time
import os
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ─── SCRAPER ───────────────────────────────────────────

def google_search(query: str):
    urls = []
    try:
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/url?q=" in href:
                actual = href.split("/url?q=")[1].split("&")[0]
                if "http" in actual:
                    urls.append(actual)
    except Exception as e:
        print(f"Google search error: {e}")
    return urls

def clean_url(url: str):
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if len(parsed.netloc) > 4:
            return base
    except:
        pass
    return None

def extract_email(html: str, url: str):
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
    for email in emails:
        if not any(skip in email for skip in ["shopify", "example", "test", "placeholder"]):
            return email
    try:
        contact_url = f"{url}/pages/contact"
        r = requests.get(contact_url, headers=HEADERS, timeout=10)
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", r.text)
        for email in emails:
            if not any(skip in email for skip in ["shopify", "example", "test"]):
                return email
    except:
        pass
    return None

def extract_store_info(url: str, keyword: str, country: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        is_password = (
            "password" in r.url or
            "Enter store password" in r.text or
            "password_page" in r.text
        )
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        name = title.text.strip().split("|")[0].strip() if title else url
        is_shopify = (
            "myshopify.com" in url or
            "cdn.shopify.com" in r.text or
            "powered by shopify" in r.text.lower()
        )
        if not is_shopify:
            return None
        if not is_password:
            return None
        email = extract_email(r.text, url)
        return {
            "name": name,
            "url": url,
            "email": email,
            "keyword": keyword,
            "country": country,
            "status": "Password Protected",
        }
    except Exception as e:
        print(f"Error extracting {url}: {e}")
        return None

def find_shopify_stores(keyword: str, country: str):
    stores = []
    queries = [
        f'"{keyword}" "powered by shopify" "{country}"',
        f'site:myshopify.com "{keyword}" "{country}"',
        f'"{keyword}" shopify store "{country}" contact',
    ]
    found_urls = set()
    for query in queries:
        try:
            results = google_search(query)
            for url in results:
                clean = clean_url(url)
                if clean and clean not in found_urls:
                    found_urls.add(clean)
                    store_data = extract_store_info(clean, keyword, country)
                    if store_data:
                        stores.append(store_data)
                    time.sleep(2)
        except Exception as e:
            print(f"Search error: {e}")
        time.sleep(3)
    return stores

# ─── SHEETS (via Apps Script) ──────────────────────────

def save_lead(store: dict):
    apps_script_url = os.environ.get("https://script.google.com/macros/s/AKfycbxyPB4XQx5mX63qQMBJHjbDlk3vBChoSW06Bkp0bDT9kFHCxAQPouD2RXULWizqLXi2xw/exec")
    try:
        requests.post(
            apps_script_url,
            json={
                "action":  "save_lead",
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
    except Exception as e:
        print(f"Save lead error: {e}")

# ─── EMAIL SENDER (via Apps Script) ────────────────────

def send_email(to: str, subject: str, body: str):
    apps_script_url = os.environ.get("https://script.google.com/macros/s/AKfycbxyPB4XQx5mX63qQMBJHjbDlk3vBChoSW06Bkp0bDT9kFHCxAQPouD2RXULWizqLXi2xw/exec")
    try:
        requests.post(
            apps_script_url,
            json={
                "action":  "send_email",
                "to":      to,
                "subject": subject,
                "body":    body,
            },
            allow_redirects=True,
            timeout=30
        )
    except Exception as e:
        print(f"Email send error: {e}")

# ─── AI EMAIL GENERATOR ────────────────────────────────

def generate_email(lead: dict):
    client = Groq(api_key=os.environ.get("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"))
    store_name = lead.get("name", "there")
    keyword    = lead.get("keyword", "your niche")
    country    = lead.get("country", "your country")

    prompt = f"""
Write a short friendly cold email to the owner of a Shopify store called "{store_name}".
They are in the {keyword} niche, based in {country}.
Their store is password protected and not launched yet.

Rules:
- Under 120 words
- Sound human, not like a template
- Mention their store name naturally
- Offer help to complete their store and start accepting payments
- End with soft CTA (reply or WhatsApp)
- No spam words

Return ONLY this JSON, nothing else:
{{"subject": "email subject here", "body": "email body here"}}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data["subject"], data["body"]
    except Exception as e:
        print(f"Email generation error: {e}")
        subject = f"Quick question about {store_name}"
        body = f"Hi,\n\nI noticed your Shopify store {store_name} isn't fully launched yet. I'd love to help you get it running and accepting payments.\n\nReply here or WhatsApp me anytime.\n\nBest regards"
        return subject, body

# ─── MAIN AGENT ────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Agent is running"}

@app.post("/start-agent")
async def start_agent(keyword: str, country: str):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "events": []}
    asyncio.create_task(run_agent(job_id, keyword, country))
    return {"job_id": job_id}

async def run_agent(job_id: str, keyword: str, country: str):
    def push(msg):
        jobs[job_id]["events"].append(msg)

    push(f"🔍 Searching for '{keyword}' stores in {country}...")
    stores = await asyncio.to_thread(find_shopify_stores, keyword, country)

    if not stores:
        push("❌ No stores found. Try different keyword.")
        jobs[job_id]["status"] = "done"
        return

    push(f"✅ Found {len(stores)} potential leads. Collecting details...")

    leads = []
    for store in stores:
        push(f"📋 Saving: {store['url']}")
        save_lead(store)
        leads.append(store)
        await asyncio.sleep(1)

    push(f"📊 All leads saved. Starting email campaign...")

    for lead in leads:
        if lead.get("email"):
            push(f"✉️ Generating email for {lead['name']}...")
            subject, body = generate_email(lead)
            send_email(lead["email"], subject, body)
            push(f"📨 Email sent to {lead['name']} ({lead['email']})")
            await asyncio.sleep(3)
        else:
            push(f"⚠️ No email found for {lead['name']} — skipped")

    push(f"🎉 Done! Total: {len(leads)} leads, Emailed: {sum(1 for l in leads if l.get('email'))}")
    jobs[job_id]["status"] = "done"

@app.get("/stream/{job_id}")
async def stream(job_id: str):
    async def event_generator():
        last_index = 0
        while True:
            job = jobs.get(job_id)
            if not job:
                break
            events = job["events"]
            while last_index < len(events):
                yield f"data: {json.dumps({'message': events[last_index]})}\n\n"
                last_index += 1
            if job["status"] == "done" and last_index >= len(events):
                yield f"data: {json.dumps({'message': '__DONE__'})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
