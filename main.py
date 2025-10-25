from fastapi import FastAPI, Form
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Lead(BaseModel):
    name: str
    phone: str
    message: str

# simple in-memory store for now
leads: List[Lead] = []

@app.get("/")
def home():
    return {"message": "Server is running!"}

@app.post("/lead")
def capture_lead(lead: Lead):
    leads.append(lead)
    return {"status": "success", "message": f"Lead captured for {lead.name}"}

@app.get("/leads")
def list_leads():
    return {"total": len(leads), "data": leads}