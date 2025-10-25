from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
import os, ssl, smtplib, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Make sure logs appear on Render
logging.basicConfig(level=logging.INFO, force=True)
log = logging.getLogger("botserver")

app = FastAPI()

class Lead(BaseModel):
    name: str
    phone: str
    message: str

leads: List[Dict[str, Any]] = []

@app.get("/")
def home():
    return {"message": "Server is running!"}

@app.post("/lead")
def capture_lead(lead: Lead, background_tasks: BackgroundTasks):
    data = {"name": lead.name, "phone": lead.phone, "message": lead.message}
    leads.append(data)
    log.info(f"[lead] captured: {data}")

    if os.getenv("SEND_EMAIL", "0") in ("1", "true", "TRUE"):
        log.info("[lead] queueing background email task")
        background_tasks.add_task(send_email_safe, data)
    else:
        log.info("[lead] SEND_EMAIL is not enabled; skipping email")

    return {"status": "success", "message": f"Lead captured for {lead.name}"}

@app.get("/leads")
def list_leads():
    return {"total": len(leads), "data": leads}

# Quick check endpoint for envs (optional to keep)
@app.get("/env-check")
def env_check():
    return {
        "owner_email_set": bool(os.getenv("OWNER_EMAIL")),
        "app_password_set": bool(os.getenv("GMAIL_APP_PASSWORD")),
        "send_email": os.getenv("SEND_EMAIL"),
    }

def send_email_safe(data: dict):
    try:
        log.info(f"[email] starting background send for {data.get('name')}")
        send_email_notification(data)
        log.info(f"[email] sent OK to {os.getenv('OWNER_EMAIL')}")
    except Exception as e:
        log.error(f"[email error] {e}")

def send_email_notification(data: dict):
    sender = os.getenv("OWNER_EMAIL")
    app_pw = os.getenv("GMAIL_APP_PASSWORD")
    if not sender or not app_pw:
        raise RuntimeError("Email env vars not set")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New Lead from {data.get('name','')}"
    msg["From"] = sender
    msg["To"] = sender

    text = (
        "New lead captured:\n\n"
        f"Name: {data.get('name')}\n"
        f"Phone: {data.get('phone')}\n"
        f"Message: {data.get('message')}\n"
    )
    msg.attach(MIMEText(text, "plain"))

    ctx = ssl.create_default_context()
    # synchronous send (background task wraps it)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=10) as server:
        server.login(sender, app_pw)
        server.send_message(msg)

# Direct email test (no background) so you see result immediately in response
@app.post("/debug-send")
def debug_send():
    test = {"name": "Debug", "phone": "000", "message": "Test email path"}
    try:
        send_email_notification(test)
        return {"ok": True, "detail": "Email sent (check inbox/spam)"}
    except Exception as e:
        # Return the error so you don’t have to open logs
        return {"ok": False, "error": str(e)}