from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3
import hashlib
import json
import os
import httpx
from datetime import datetime, timedelta
import jwt
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Learning Resource Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route to serve the frontend
@api_router.get("/")
async def read_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "public", "index.html"))

# Mount static files (for any other assets you might add later)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public")), name="static")

SECRET_KEY = "learning-app-secret-2024"
ALGORITHM = "HS256"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/learning.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "learning.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            topic TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, link, topic),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS resource_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, resource_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (resource_id) REFERENCES custom_resources(id) ON DELETE CASCADE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            level TEXT NOT NULL,
            goal TEXT NOT NULL,
            time TEXT NOT NULL,
            roadmap_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            day INTEGER NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, week, day),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Insert demo user
    try:
        demo_pw = hashlib.sha256("demo123".encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO users (email, password) VALUES (?, ?)", ("demo@learn.ai", demo_pw))
    except:
        pass
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    return verify_token(token)

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RoadmapRequest(BaseModel):
    topic: str
    level: str
    time: str

class ResourceRequest(BaseModel):
    type: str
    title: str
    link: str
    topic: str

class ProgressRequest(BaseModel):
    resource_id: int
    progress: int

class DailyProgressRequest(BaseModel):
    week: int
    day: int
    completed: bool

class DailyProgressItem(BaseModel):
    week: int
    day: int
    completed: bool
    updated_at: str

async def call_groq(topic: str, level: str, time: str) -> dict:
    prompt = f"""User wants to learn: {topic}
Level: {level}
Time per day: {time}

STRICT RULES:
- Generate 4-6 week roadmap
- Each week must have 2-4 topics
- Practice must include specific numbers (e.g., solve 10 problems)
- Maintain progressive difficulty
- Avoid vague phrases
- CRITICAL: Provide at least 10 high-quality learning resources in total across the 'youtube' and 'platforms' categories.

Return ONLY valid JSON with no markdown, no explanation, no code fences:
{{
  "roadmap": [
    {{
      "week": "Week 1",
      "topics": ["Topic A", "Topic B"],
      "practice": "Solve 10 problems on X, build 1 mini project on Y"
    }}
  ],
  "resources": {{
    "youtube": ["Channel Name - Playlist Title (URL or description)", "Channel 2 - Topic"],
    "platforms": ["LeetCode - Practice problems", "Coursera - Course name", "GeeksForGeeks - Reference"]
  }},
  "daily_plan": "Hour 1: Study theory. Hour 2: Practice problems. Hour 3: Review and notes."
}}"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(GROQ_API_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().rstrip("```").strip()
        return json.loads(text)

@api_router.on_event("startup")
def startup():
    init_db()

@api_router.post("/register")
def register(req: RegisterRequest):
    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)",
                      (req.email.lower(), hash_password(req.password)))
            conn.commit()
            user_id = c.lastrowid
            token = create_token(user_id, req.email.lower())
            return {"status": "success", "token": token, "email": req.email.lower()}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Email already registered")

@api_router.post("/login")
def login(req: LoginRequest):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, password FROM users WHERE email = ?", (req.email.lower(),))
        user = c.fetchone()
        if not user or user["password"] != hash_password(req.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_token(user["id"], user["email"])
        return {"status": "success", "token": token, "email": user["email"]}

@api_router.post("/generate-roadmap")
async def generate_roadmap(req: RoadmapRequest, current_user=Depends(get_current_user)):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured on server")

    result = None
    last_error = None

    for attempt in range(2):
        try:
            result = await call_groq(req.topic, req.level, req.time)
            break
        except json.JSONDecodeError as e:
            last_error = f"AI returned invalid JSON: {str(e)}"
            if attempt == 1:
                raise HTTPException(status_code=502, detail=last_error)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Groq API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    user_id = int(current_user["sub"])
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO learning_plan (user_id, topic, level, goal, time, roadmap_json) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, req.topic, req.level, "", req.time, json.dumps(result))
        )
        conn.commit()

    return {"status": "success", "data": result}

@api_router.get("/my-plans")
def get_my_plans(current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, topic, level, goal, time, roadmap_json, created_at FROM learning_plan WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )
        plans = c.fetchall()
    return {
        "status": "success",
        "plans": [
            {
                "id": p["id"],
                "topic": p["topic"],
                "level": p["level"],
                "goal": p["goal"],
                "time": p["time"],
                "roadmap": json.loads(p["roadmap_json"]),
                "created_at": p["created_at"]
            }
            for p in plans
        ]
    }

@api_router.get("/health")
def health():
    return {"status": "ok"}

@api_router.post("/resources")
def add_resource(req: ResourceRequest, current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    title = req.title.strip()
    link = req.link.strip()
    topic = req.topic.strip()
    rtype = req.type.strip()
    
    if not title or not link:
        return {"status": "error", "message": "Title and link must not be empty"}
    
    if not (link.startswith("http://") or link.startswith("https://")):
        return {"status": "error", "message": "Link must be a valid URL starting with http:// or https://"}

    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO custom_resources (user_id, type, title, link, topic) VALUES (?, ?, ?, ?, ?)",
                      (user_id, rtype, title, link, topic.lower()))
            conn.commit()
            return {"status": "success", "message": "Resource added successfully", "data": {"id": c.lastrowid}}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "Resource already exists for this topic"}

@api_router.get("/resources")
def get_resources(current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, type, title, link, topic FROM custom_resources WHERE user_id = ? ORDER BY id DESC", (user_id,))
        resources = [dict(row) for row in c.fetchall()]
        return {"status": "success", "data": resources}

@api_router.put("/resources/{res_id}")
def update_resource(res_id: int, req: ResourceRequest, current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    title = req.title.strip()
    link = req.link.strip()
    topic = req.topic.strip()
    rtype = req.type.strip()
    
    if not title or not link:
        return {"status": "error", "message": "Title and link must not be empty"}
    if not (link.startswith("http://") or link.startswith("https://")):
        return {"status": "error", "message": "Link must be a valid URL starting with http:// or https://"}

    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute("UPDATE custom_resources SET type=?, title=?, link=?, topic=? WHERE id=? AND user_id=?", 
                      (rtype, title, link, topic.lower(), res_id, user_id))
            if c.rowcount == 0:
                return {"status": "error", "message": "Resource not found or unauthorized"}
            conn.commit()
            return {"status": "success", "message": "Resource updated successfully", "data": {}}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "Resource already exists for this topic"}

@api_router.delete("/resources/{res_id}")
def delete_resource(res_id: int, current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM custom_resources WHERE id=? AND user_id=?", (res_id, user_id))
        if c.rowcount == 0:
            return {"status": "error", "message": "Resource not found or unauthorized"}
        conn.commit()
        return {"status": "success", "message": "Resource deleted successfully"}

@api_router.post("/progress")
def update_progress(req: ProgressRequest, current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    prog = req.progress
    
    if not isinstance(prog, int) or prog < 0 or prog > 100:
        return {"status": "error", "message": "Invalid progress value"}
        
    status_label = "Completed" if prog == 100 else ("Not Started" if prog == 0 else "In Progress")
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM custom_resources WHERE id=? AND user_id=?", (req.resource_id, user_id))
        if not c.fetchone():
            return {"status": "error", "message": "Resource not found or unauthorized"}

        c.execute("""
            INSERT INTO resource_progress (user_id, resource_id, progress, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, resource_id) DO UPDATE SET
                progress=excluded.progress,
                updated_at=excluded.updated_at
        """, (user_id, req.resource_id, prog, now_str))
        conn.commit()
        
        return {
            "status": "success",
            "data": {
                "resource_id": req.resource_id,
                "progress": prog,
                "status": status_label,
                "updated_at": now_str
            }
        }

        return {"status": "success", "data": data}

@api_router.get("/progress")
def get_progress(current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT resource_id, progress, updated_at FROM resource_progress WHERE user_id=?", (user_id,))
        records = c.fetchall()
        
        data = []
        for r in records:
            prog = r["progress"]
            st = "Completed" if prog == 100 else ("Not Started" if prog == 0 else "In Progress")
            data.append({
                "resource_id": r["resource_id"],
                "progress": prog,
                "status": st,
                "updated_at": r["updated_at"]
            })
            
        return {"status": "success", "data": data}

@api_router.post("/daily-progress")
def update_daily_progress(req: DailyProgressRequest, current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    if not (1 <= req.day <= 6):
        raise HTTPException(status_code=400, detail="Day must be between 1 and 6")
    
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO daily_progress (user_id, week, day, completed, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, week, day) DO UPDATE SET
                completed=excluded.completed,
                updated_at=excluded.updated_at
        """, (user_id, req.week, req.day, 1 if req.completed else 0, now_str))
        conn.commit()
    return {"status": "success"}

@api_router.get("/daily-progress")
def get_daily_progress(current_user=Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT week, day, completed, updated_at FROM daily_progress WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        return {
            "status": "success",
            "data": [
                {
                    "week": r["week"],
                    "day": r["day"],
                    "completed": bool(r["completed"]),
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]
        }

