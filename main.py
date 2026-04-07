from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
import os

import models
from database import get_db, engine

app = FastAPI(debug=True)

# 🔥 FIX: database tables auto create
models.Base.metadata.create_all(bind=engine)

# 🔥 FIX: safe absolute paths (Render friendly)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ── HELPER ─────────────────────────────────────────────

def get_user_id(request: Request):
    try:
        return int(request.cookies.get("user_id", 0))
    except:
        return 0

def require_role(request: Request, role: str):
    user_id = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role")

    if not user_id or user_role != role:
        return False
    return True

def render(template_name: str, request: Request, context: dict = {}):
    data = {"request": request}
    data.update(context)
    return templates.TemplateResponse(template_name, data)

# ── AUTH ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return render("login.html", request, {"error": None})

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip()
    password = password.strip()

    user = db.query(models.User).filter(func.lower(models.User.email) == email.lower()).first()

    if not user or user.password.strip() != password:
        return render("login.html", request, {"error": "Invalid email or password"})

    response = RedirectResponse(url=f"/{user.role}/dashboard", status_code=302)
    response.set_cookie("user_id", str(user.id))
    response.set_cookie("user_role", user.role)
    response.set_cookie("user_name", user.name)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("user_id")
    response.delete_cookie("user_role")
    response.delete_cookie("user_name")
    return response

# ── ADMIN ─────────────────────────────────────────────

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    return render("dashboard.html", request, {
        "teacher_count": db.query(models.User).filter(models.User.role == "teacher").count(),
        "student_count": db.query(models.User).filter(models.User.role == "student").count(),
        "course_count": db.query(models.Course).count(),
        "user_name": request.cookies.get("user_name", "Admin"),
    })

@app.get("/admin/teachers", response_class=HTMLResponse)
def admin_teachers(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    return render("teachers.html", request, {
        "teachers": db.query(models.User).filter(models.User.role == "teacher").all(),
        "user_name": request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/teachers/add")
def add_teacher(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    db.add(models.User(name=name, email=email, password=password, role="teacher"))
    db.commit()
    return RedirectResponse(url="/admin/teachers", status_code=302)

@app.post("/admin/teachers/delete/{teacher_id}")
def delete_teacher(request: Request, teacher_id: int, db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    t = db.query(models.User).filter(models.User.id == teacher_id).first()
    if t:
        db.delete(t)
        db.commit()
    return RedirectResponse(url="/admin/teachers", status_code=302)

@app.get("/admin/students", response_class=HTMLResponse)
def admin_students(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    return render("student.html", request, {
        "students": db.query(models.User).filter(models.User.role == "student").all(),
        "user_name": request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/students/add")
def add_student(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    db.add(models.User(name=name, email=email, password=password, role="student"))
    db.commit()
    return RedirectResponse(url="/admin/students", status_code=302)

# ── STUDENT ASSIGNMENTS (🔥 FIXED) ─────────────────────

@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    sid = get_user_id(request)

    assignments = db.query(models.Assignment).all()
    subs = db.query(models.Submission).filter(models.Submission.student_id == sid).all()

    # 🔥 FINAL SAFE FIX
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
        "submissions": submissions,
        "user_name": request.cookies.get("user_name", "Student"),
    })

@app.post("/student/assignments/submit")
def submit_assignment(request: Request, assignment_id: int = Form(...), answer: str = Form(...), db: Session = Depends(get_db)):
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

    return RedirectResponse(url="/student/assignments", status_code=302)