from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

import models
from database import get_db, engine, SessionLocal

app = FastAPI()

# =========================
# STATIC + TEMPLATES
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# =========================
# STARTUP (DB + ADMIN)
# =========================
@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Admin auto create
    if not db.query(models.User).filter(models.User.email == "admin@edu.com").first():
        db.add(models.User(
            name="Super Admin",
            email="admin@edu.com",
            password="admin123",
            role="admin"
        ))
        db.commit()
        print("✅ Admin created")

    db.close()


# =========================
# HELPER
# =========================
def render(template, request, data={}):
    return templates.TemplateResponse(template, {
        "request": request,
        **data
    })


# =========================
# AUTH
# =========================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render("login.html", request)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render("login.html", request)


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    email = email.strip().lower()
    password = password.strip()

    user = db.query(models.User).filter(
        func.lower(models.User.email) == email
    ).first()

    if not user or (user.password or "").strip() != password:
        return render("login.html", request, {"error": "Invalid email or password"})

    res = RedirectResponse(url=f"/{user.role}/dashboard", status_code=302)

    res.set_cookie("user_id", str(user.id))
    res.set_cookie("user_role", user.role)
    res.set_cookie("user_name", user.name)

    return res


@app.get("/logout")
def logout():
    res = RedirectResponse("/")
    res.delete_cookie("user_id")
    res.delete_cookie("user_role")
    res.delete_cookie("user_name")
    return res


# =========================
# DASHBOARDS
# =========================
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    return render("dashboard.html", request)


@app.get("/teacher/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request):
    return render("dashboard_t.html", request)


@app.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard(request: Request):
    return render("student_dashboard.html", request)


# =========================
# STUDENT ASSIGNMENTS (FIXED)
# =========================
@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):

    assignments = db.query(models.Assignment).all()
    submissions = db.query(models.Submission).all()

    return render("assignments.html", request, {
        "assignments": assignments,
        "submissions": submissions
    })


@app.post("/student/assignments/submit")
def submit_assignment(
    assignment_id: int = Form(...),
    answer: str = Form(...),
    db: Session = Depends(get_db)
):

    sub = models.Submission(
        assignment_id=assignment_id,
        answer=answer,
        submitted_at=str(datetime.now())
    )

    db.add(sub)
    db.commit()

    return RedirectResponse("/student/assignments", status_code=302)


# =========================
# FIX: REMOVE 405 ERROR
# =========================
@app.get("/{full_path:path}")
def catch_all():
    return RedirectResponse("/")
