import os
import json
import sqlite3
import secrets
import logging

from fastapi import FastAPI, Header, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_ID = os.getenv("ADMIN_ID","admin123")
ADMIN_TOKEN = None
def get_db():
    conn = sqlite3.connect("complaints.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    regNo TEXT,
    block TEXT,
    room TEXT,
    text TEXT,
    category TEXT,
    confidence INTEGER,
    department TEXT,
    status TEXT,
    resolution TEXT,   -- ✅ ADD THIS
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

    conn.commit()
    conn.close()


create_table()

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

class Complaint(BaseModel):
    name: str
    regNo: str
    block: str
    room: str
    desc: str = Field(..., min_length=5, max_length=500)


prompt_template = PromptTemplate(
    template="""
You are an AI campus complaint classifier.

Categories:
1. Bathroom & Hygiene
2. Anti-Ragging & Safety
3. Mess & Food Quality
4. Academic Issues
5. Infrastructure/Maintenance
6. Other

Return ONLY valid JSON:
{
  "category": "...",
  "confidence": 0-100
}

Complaint: {complaint}
""",
    input_variables=["complaint"]
)

def classify(text):
    try:
        prompt = prompt_template.format(complaint=text)
        response = llm.invoke(prompt)
        return json.loads(response.content.strip())
    except:
        return {"category": "Other", "confidence": 50}


def route(category):
    mapping = {
        "Bathroom & Hygiene": "Cleaning Staff",
        "Anti-Ragging & Safety": "Security Team",
        "Mess & Food Quality": "Mess Department",
        "Academic Issues": "Academic Office",
        "Infrastructure/Maintenance": "Maintenance Team",
        "Other": "Admin"
    }
    return mapping.get(category, "Admin")


@app.get("/")
def home():
    return {"message": "Campus Care AI Backend Running"}

@app.get("/health")
def health():
    return {"status": "OK"}

@app.post("/submit")
def submit(data: Complaint):
    result = classify(data.desc)

    category = result["category"]
    confidence = result["confidence"]

    if confidence < 60:
        department = "Admin"
    else:
        department = route(category)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO complaints 
        (name, regNo, block, room, text, category, confidence, department, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.name,
        data.regNo,
        data.block,
        data.room,
        data.desc,
        category,
        confidence,
        department,
        "Submitted"
    ))

    conn.commit()
    complaint_id = cur.lastrowid
    conn.close()

    return {
        "success": True,
        "trackingId": f"CC-{complaint_id}",
        "data": {
            "id": complaint_id,
            "category": category,
            "confidence": confidence,
            "assigned_to": department,
            "status": "Submitted"
        }
    }

@app.get("/track/{complaint_id}")
def track(complaint_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"success": False, "error": "Not found"}

    return {
        "success": True,
        "data": dict(row)
    }

@app.post("/admin/login")
def admin_login(payload: dict = Body(...)):
    global ADMIN_TOKEN

    admin_id = payload.get("uniqueId")

    if admin_id == ADMIN_ID:
        ADMIN_TOKEN = secrets.token_hex(16)
        return {"success": True, "token": ADMIN_TOKEN}

    return {"success": False, "error": "Invalid admin ID"}

def verify(token: str):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/admin/complaints")
def admin_all(token: str = Header(...)):
    verify(token)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM complaints ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()

    return {
        "success": True,
        "data": [dict(r) for r in rows]
    }
from pydantic import BaseModel

class UpdateRequest(BaseModel):
    status: str
    resolution: str

@app.put("/admin/update/{cid}")
def update_status(
    cid: int,
    data: UpdateRequest,
    token: str = Header(...)
):
    verify(token)

    if data.status not in ["Submitted", "In Progress", "Resolved", "Closed"]:
        return {"success": False}

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE complaints SET status=?, resolution=? WHERE id=?
    """, (data.status, data.resolution, cid))

    conn.commit()
    conn.close()

    return {"success": True}

@app.put("/user/confirm/{cid}")
def close(cid: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT status FROM complaints WHERE id=?", (cid,))
    row = cur.fetchone()

    if not row:
        return {"success": False, "error": "Not found"}

    if row["status"] != "Resolved":
        return {"success": False, "error": "Not resolved yet"}

    cur.execute("""
        UPDATE complaints SET status='Closed' WHERE id=?
    """, (cid,))

    conn.commit()
    conn.close()

    return {"success": True, "message": "Closed by user"}