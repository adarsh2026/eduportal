from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import urllib.parse

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
# HELPER (FIXED ✅)
# =========================
def render(template, request, data=None):
    context = data or {}
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context
    )


# =========================
# COOKIE HELPER (NEW ✅)
# =========================
def get_user_from_cookies(request: Request):
    return {
        "user_id": request.cookies.get("user_id", ""),
        "user_role": request.cookies.get("user_role", ""),
        "user_name": urllib.parse.unquote(request.cookies.get("user_name", "Guest")),
    }


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
    res.set_cookie("user_name", urllib.parse.quote(str(user.name)))  # ✅ Encoded

    return res


@app.get("/logout")
def logout():
    res = RedirectResponse("/")
    res.delete_cookie("user_id")
    res.delete_cookie("user_role")
    res.delete_cookie("user_name")
    return res


# =========================
# DASHBOARDS (FIXED ✅ - user_name ab pass ho raha hai)
# =========================
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = get_user_from_cookies(request)
    return render("dashboard.html", request, user)


@app.get("/teacher/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request):
    user = get_user_from_cookies(request)
    return render("dashboard_t.html", request, user)


@app.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard(request: Request):
    user = get_user_from_cookies(request)
    return render("student_dashboard.html", request, user)


# =========================
# STUDENT ASSIGNMENTS
# =========================
@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    assignments = db.query(models.Assignment).all()
    submissions = db.query(models.Submission).all()

    return render("assignments.html", request, {
        **user,
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
# CATCH ALL (FIXED ✅)
# =========================
@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return RedirectResponse("/")
