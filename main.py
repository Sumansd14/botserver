from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import smtplib, ssl, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
def capture_lead(lead: Lead):
    leads.append(lead)
    send_email_notification(lead)
    return {"status": "success", "message": f"Lead captured for {lead.name}"}

@app.get("/leads")
def list_leads():
    return {"total": len(leads), "data": leads}

def send_email_notification(lead: Lead):
    sender = os.getenv("OWNER_EMAIL")
    password = os.getenv("GMAIL_APP_PASSWORD")
    receiver = sender

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New Lead from {lead.name}"
    msg["From"] = sender
    msg["To"] = receiver

    text = f"""
    New lead captured:

    Name: {lead.name}
    Phone: {lead.phone}
    Message: {lead.message}
    """
    msg.attach(MIMEText(text, "plain"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password)
        server.send_message(msg)