from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import os

import models
from database import get_db, engine

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ---------- FIXED RENDER FUNCTION ----------

def render(template, request, context=None):
    if context is None:
        context = {}
    context["request"] = request
    return templates.TemplateResponse(template, context)

# ---------- LOGIN ----------

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return render("login.html", request, {})  # 🔥 FIX HERE

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(func.lower(models.User.email) == email.lower()).first()

    if not user or user.password != password:
        return render("login.html", request, {"error": "Invalid credentials"})

    res = RedirectResponse(f"/{user.role}/dashboard", status_code=302)
    res.set_cookie("user_id", str(user.id))
    res.set_cookie("user_role", user.role)
    return res

# ---------- STUDENT ASSIGNMENTS (UNCHANGED SAFE CODE) ----------

@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):

    if request.cookies.get("user_role") != "student":
        return RedirectResponse("/", status_code=302)

    sid = int(request.cookies.get("user_id", 0))

    assignments = db.query(models.Assignment).all()
    subs = db.query(models.Submission).filter(models.Submission.student_id == sid).all()

    submissions = {}

    for s in subs:
        key = s.assignment_id

        if isinstance(key, tuple):
            key = key[0]

        if isinstance(key, dict):
            key = list(key.values())[0]

        try:
            key = int(key)
            submissions[key] = s
        except:
            continue

    return render("assigment_sub.html", request, {
        "assignments": assignments,
        "submissions": submissions
    })

# ---------- SUBMIT ----------

@app.post("/student/assignments/submit")
def submit_assignment(request: Request,
                      assignment_id: int = Form(...),
                      answer: str = Form(...),
                      db: Session = Depends(get_db)):

    if request.cookies.get("user_role") != "student":
        return RedirectResponse("/", status_code=302)

    sid = int(request.cookies.get("user_id", 0))

    existing = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment_id,
        models.Submission.student_id == sid
    ).first()

    if not existing:
        db.add(models.Submission(
            assignment_id=assignment_id,
            student_id=sid,
            answer=answer,
            submitted_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        db.commit()

    return RedirectResponse("/student/assignments", status_code=302)