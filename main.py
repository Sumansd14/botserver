import os
import ssl
import smtplib
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Logging setup
logging.basicConfig(level=logging.INFO, force=True)
log = logging.getLogger("botserver")

app = FastAPI(title="Botserver")

# Data model
class Lead(BaseModel):
    name: str
    phone: str
    message: str

# In-memory store
LEADS: List[Dict[str, Any]] = []

@app.get("/")
def home():
    return {"message": "Server is running!"}

@app.get("/form", response_class=HTMLResponse)
def form():
    return """
    <!doctype html><html><body style="font-family:sans-serif;max-width:480px;margin:40px auto">
      <h2>Contact / Lead</h2>
      <form onsubmit="send(event)">
        <input name="name" placeholder="Your name" required style="width:100%;padding:8px;margin:6px 0">
        <input name="phone" placeholder="Phone" required style="width:100%;padding:8px;margin:6px 0">
        <textarea name="message" placeholder="Message" style="width:100%;padding:8px;margin:6px 0"></textarea>
        <button type="submit" style="padding:10px 16px">Send</button>
      </form>
      <pre id="out" style="white-space:pre-wrap;background:#f6f6f6;padding:10px;border-radius:6px"></pre>
      <script>
        async function send(e){
          e.preventDefault();
          const f = e.target;
          const payload = {name:f.name.value, phone:f.phone.value, message:f.message.value};
          const r = await fetch('/lead', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify(payload)
          });
          document.getElementById('out').textContent = await r.text();
          f.reset();
        }
      </script>
    </body></html>
    """

@app.post("/lead")
def capture_lead(lead: Lead, background_tasks: BackgroundTasks):
    data = lead.dict()
    LEADS.append(data)
    log.info(f"[lead] captured: {data}")
    if os.getenv("SEND_EMAIL", "0") in ("1", "true", "TRUE"):
        background_tasks.add_task(send_email_safe, data)
    return {"status": "success", "message": f"Lead captured for {data['name']}"}

@app.get("/leads")
def list_leads():
    return {"total": len(LEADS), "data": LEADS}

@app.get("/env-check")
def env_check():
    return {
        "owner_email_set": bool(os.getenv("OWNER_EMAIL")),
        "app_password_set": bool(os.getenv("GMAIL_APP_PASSWORD")),
        "send_email": os.getenv("SEND_EMAIL"),
    }

@app.post("/debug-send")
def debug_send():
    test = {"name": "Debug", "phone": "000", "message": "Test email path"}
    try:
        send_email_notification(test)
        return {"ok": True, "detail": "Email sent (check inbox/spam)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_email_safe(data: dict):
    try:
        send_email_notification(data)
    except Exception as e:
        log.error(f"[email error] {e}")

import os, requests

def send_email_notification(data: dict):
    url = os.getenv("MAILER_URL")
    secret = os.getenv("MAILER_SECRET")
    if not url or not secret:
        raise RuntimeError("Mailer config not set")

    r = requests.post(
        url,
        json={
            "name": data.get("name"),
            "phone": data.get("phone"),
            "message": data.get("message")
        },
        headers={
            "X-Mailer-Secret": secret,
            "Content-Type": "application/json"
        },
        timeout=8,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"Mailer failed: {r.status_code} {r.text}")