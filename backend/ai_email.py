import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def generate_email(lead: dict):
    store_name = lead.get("name", "there")
    keyword = lead.get("keyword", "your niche")
    country = lead.get("country", "your country")
    status = lead.get("status", "")

    if "Password" in status:
        situation = "you have built your Shopify store but it's still password protected and not yet launched"
    else:
        situation = "you have built your Shopify store but haven't set up a payment gateway yet"

    prompt = f"""
Write a short, friendly cold email to the owner of a Shopify store called "{store_name}".
They are in the {keyword} niche, based in {country}.
The situation is: {situation}.

The email should:
- Be under 120 words
- Sound human, not like a template
- Mention their store name naturally
- Offer help to complete their store setup and start accepting payments
- End with a soft call to action (reply to this email or WhatsApp)
- No fake urgency, no spammy words

Return ONLY this JSON, nothing else:
{{
  "subject": "email subject here",
  "body": "email body here"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        import json
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data["subject"], data["body"]
    except Exception as e:
        print(f"Email generation error: {e}")
        subject = f"Quick question about {store_name}"
        body = f"Hi,\n\nI noticed your Shopify store {store_name} isn't fully set up yet. I'd love to help you get it running and accepting payments.\n\nReply here or WhatsApp me anytime.\n\nBest regards"
        return subject, body
