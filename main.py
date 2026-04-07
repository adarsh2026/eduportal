from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import os

import models
from database import get_db, engine

app = FastAPI(debug=True)

# DB init
models.Base.metadata.create_all(bind=engine)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ───────── HELPERS ─────────

def get_user_id(request: Request):
    try:
        return int(request.cookies.get("user_id", 0))
    except:
        return 0

def require_role(request: Request, role: str):
    user_id = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role")
    return user_id and user_role == role

def render(template, request, context={}):
    data = {"request": request}
    data.update(context)
    return templates.TemplateResponse(template, data)

# ───────── AUTH ─────────

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return render("login.html", request, {"error": None})

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(func.lower(models.User.email) == email.lower()).first()

    if not user or user.password != password:
        return render("login.html", request, {"error": "Invalid credentials"})

    res = RedirectResponse(f"/{user.role}/dashboard", status_code=302)
    res.set_cookie("user_id", str(user.id))
    res.set_cookie("user_role", user.role)
    res.set_cookie("user_name", user.name)
    return res

@app.get("/logout")
def logout():
    res = RedirectResponse("/", status_code=302)
    res.delete_cookie("user_id")
    res.delete_cookie("user_role")
    res.delete_cookie("user_name")
    return res

# ───────── STUDENT ASSIGNMENTS (🔥 FINAL FIX) ─────────

@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    sid = get_user_id(request)

    assignments = db.query(models.Assignment).all()
    subs = db.query(models.Submission).filter(models.Submission.student_id == sid).all()

    submissions = {}

    for s in subs:
        key = s.assignment_id

        # 🔥 FULL SAFE HANDLING (tuple/dict fix)
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

# ───────── SUBMIT ─────────

@app.post("/student/assignments/submit")
def submit_assignment(request: Request,
                      assignment_id: int = Form(...),
                      answer: str = Form(...),
                      db: Session = Depends(get_db)):

    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    sid = get_user_id(request)

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