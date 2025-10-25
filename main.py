from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
import os, ssl, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()

class Lead(BaseModel):
    name: str
    phone: str
    message: str

# store plain dicts (keeps it simple and serializable)
leads: List[Dict[str, Any]] = []

@app.get("/")
def home():
    return {"message": "Server is running!"}

@app.post("/lead")
def capture_lead(lead: Lead, background_tasks: BackgroundTasks):
    data = {"name": lead.name, "phone": lead.phone, "message": lead.message}
    leads.append(data)

    if os.getenv("SEND_EMAIL", "0") in ("1", "true", "TRUE"):
        # fire-and-forget so the API responds instantly
        background_tasks.add_task(send_email_safe, data)

    return {"status": "success", "message": f"Lead captured for {lead.name}"}

@app.get("/leads")
def list_leads():
    return {"total": len(leads), "data": leads}

def send_email_safe(data: dict):
    try:
        send_email_notification(data)
    except Exception as e:
        # Don't crash the app; check Render logs if email fails
        print(f"[email error] {e}")

def send_email_notification(data: dict):
    sender = os.getenv("OWNER_EMAIL")
    app_pw  = os.getenv("GMAIL_APP_PASSWORD")
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

    context = ssl.create_default_context()
    # timeout so it never stalls the worker
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=10) as server:
        server.login(sender, app_pw)
        server.send_message(msg)

@app.get("/env-check")
def env_check():
    import os
    return {
        "owner_email_set": bool(os.getenv("OWNER_EMAIL")),
        "app_password_set": bool(os.getenv("GMAIL_APP_PASSWORD")),
        "send_email": os.getenv("SEND_EMAIL")
    }        