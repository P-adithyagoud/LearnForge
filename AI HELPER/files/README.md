# LearnForge — AI Learning Resource Generator

A full-stack personalized learning planner powered by Groq AI.

## Project Structure

learnforge/
├── api/
│   └── index.py          ← your FastAPI app (Vercel serverless function)
├── index.html            ← frontend (at root, NOT in /public/)
├── vercel.json
└── requirements.txt

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3.10+ · FastAPI · Uvicorn    |
| Frontend | HTML5 · CSS3 · Vanilla JavaScript   |
| Database | SQLite (no setup needed)            |
| AI       | Groq API (llama3-70b-8192)          |
| Auth     | JWT (PyJWT)                         |

---

## Quick Start

### 1. Get a Groq API Key (Free)

1. Go to https://console.groq.com
2. Sign up and create an API key
3. Copy it — you'll need it below

### 2. Run the App

```bash
# Clone / download this project, then:
cd learnforge

# Set your API key
export GROQ_API_KEY=gsk_your_key_here

# Run everything
chmod +x run.sh
./run.sh
```

### 3. Open in Browser

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs

### 4. Demo Credentials

| Email         | Password |
|---------------|----------|
| demo@learn.ai | demo123  |

---

## Manual Setup (if run.sh doesn't work)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install fastapi uvicorn httpx pyjwt python-multipart

# 3. Start backend (Terminal 1)
cd backend
export GROQ_API_KEY=gsk_your_key_here
uvicorn main:app --reload --port 8000

# 4. Serve frontend (Terminal 2)
cd frontend
python3 -m http.server 3000
```

---

## API Reference

### POST /register
```json
{ "email": "user@example.com", "password": "secret123" }
```

### POST /login
```json
{ "email": "user@example.com", "password": "secret123" }
```
Returns: `{ "status": "success", "token": "...", "email": "..." }`

### POST /generate-roadmap *(requires Bearer token)*
```json
{
  "topic": "Machine Learning",
  "level": "Beginner",
  "goal": "Placements",
  "time": "2 hours"
}
```
Returns:
```json
{
  "status": "success",
  "data": {
    "roadmap": [
      {
        "week": "Week 1",
        "topics": ["Python basics", "NumPy & Pandas"],
        "practice": "Complete 15 NumPy exercises, build 1 data analysis notebook"
      }
    ],
    "resources": {
      "youtube": ["3Blue1Brown - Neural Networks playlist"],
      "platforms": ["Kaggle - Free ML courses", "fast.ai", "Coursera - ML Specialization"]
    },
    "daily_plan": "Hour 1: Watch lecture. Hour 2: Practice exercises."
  }
}
```

### GET /my-plans *(requires Bearer token)*
Returns all saved plans for the logged-in user.

---

## Features

- **Login / Register** — JWT-based auth, stored in localStorage
- **Dashboard** — Clean form with topic, level, goal, time inputs
- **Roadmap View** — Week-by-week cards with color coding
- **Resources Tab** — YouTube channels + learning platforms
- **Daily Plan Tab** — Structured hourly breakdown
- **History** — All previously generated plans, click to reload
- **Error Handling** — Groq JSON retry logic, user-friendly error messages
- **Loading State** — Spinner + disabled button during generation

---

## Changing the AI Model

In `backend/main.py`, find:
```python
"model": "llama3-70b-8192",
```
You can change this to any Groq-supported model:
- `llama3-8b-8192` (faster, lighter)
- `mixtral-8x7b-32768` (longer context)

---

## Deploying

### Backend (e.g. Railway / Render)
- Set `GROQ_API_KEY` as an environment variable
- Run: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend
- Update `API_BASE` in `index.html` to your deployed backend URL
- Host on Netlify, Vercel, or any static host

---

## Database Schema

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE learning_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    level TEXT NOT NULL,
    goal TEXT NOT NULL,
    time TEXT NOT NULL,
    roadmap_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```
