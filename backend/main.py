from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
import json
import uuid
from scraper import find_shopify_stores
from sheets import save_lead
from ai_email import generate_email
from emailer import send_email

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}

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
        push(f"📋 Checking: {store['url']}")
        save_lead(store)
        leads.append(store)
        await asyncio.sleep(1)

    push(f"📊 All leads saved to Google Sheet. Starting email campaign...")

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
