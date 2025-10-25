from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List
import os, requests

app = FastAPI()

class Lead(BaseModel):
    name: str
    phone: str
    message: str

leads: List[Lead] = []

@app.get("/")
def home():
    return {"message": "Server is running!"}

@app.post("/lead")
def capture_lead(lead: Lead, background_tasks: BackgroundTasks):
    # store
    leads.append(lead)
    # send only primitives to background task
    background_tasks.add_task(send_whatsapp_notification_safe, lead.dict())
    return {"status": "success", "message": f"Lead captured for {lead.name}"}

@app.get("/leads")
def list_leads():
    return {"total": len(leads), "data": [l.dict() for l in leads]}

def send_whatsapp_notification_safe(lead_data: dict):
    try:
        send_whatsapp_notification(lead_data)
    except Exception as e:
        print(f"[whatsapp error] {e}")

def send_whatsapp_notification(lead_data: dict):
    token    = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    owner    = os.getenv("OWNER_PHONE_E164")
    if not token or not phone_id or not owner:
        raise RuntimeError("WhatsApp env vars not set")

    url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    body_text = (
        "📥 *New Lead Captured*\n"
        f"*Name:* {lead_data.get('name')}\n"
        f"*Phone:* {lead_data.get('phone')}\n"
        f"*Message:* {lead_data.get('message')}"
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": owner,
        "type": "text",
        "text": {"preview_url": False, "body": body_text}
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # short timeout so we never hang
    r = requests.post(url, headers=headers, json=payload, timeout=5)
    if r.status_code >= 300:
        raise RuntimeError(f"WA send failed: {r.status_code} {r.text}")