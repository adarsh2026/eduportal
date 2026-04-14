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
# HELPER
# =========================
def render(template, request, data=None):
    context = data or {}
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context
    )

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
    res.set_cookie("user_name", urllib.parse.quote(str(user.name)))
    return res


@app.get("/logout")
def logout():
    res = RedirectResponse("/")
    res.delete_cookie("user_id")
    res.delete_cookie("user_role")
    res.delete_cookie("user_name")
    return res


# =========================
# ADMIN ROUTES
# =========================
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = get_user_from_cookies(request)
    return render("dashboard.html", request, user)


@app.get("/admin/programmes", response_class=HTMLResponse)
def admin_programmes(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    courses = db.query(models.Course).all() if hasattr(models, 'Course') else []
    return render("course.html", request, {**user, "courses": courses})


@app.post("/admin/programmes/add")
def add_programme(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    if hasattr(models, 'Course'):
        db.add(models.Course(name=name))
        db.commit()
    return RedirectResponse("/admin/programmes", status_code=302)


@app.post("/admin/programmes/delete/{id}")
def delete_programme(id: int, db: Session = Depends(get_db)):
    if hasattr(models, 'Course'):
        course = db.query(models.Course).filter(models.Course.id == id).first()
        if course:
            db.delete(course)
            db.commit()
    return RedirectResponse("/admin/programmes", status_code=302)


@app.get("/admin/teachers", response_class=HTMLResponse)
def admin_teachers(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    teachers = db.query(models.User).filter(models.User.role == "teacher").all()
    return render("teachers.html", request, {**user, "teachers": teachers})


@app.post("/admin/teachers/add")
def add_teacher(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if not existing:
        db.add(models.User(name=name, email=email, password=password, role="teacher"))
        db.commit()
    return RedirectResponse("/admin/teachers", status_code=302)


@app.post("/admin/teachers/delete/{id}")
def delete_teacher(id: int, db: Session = Depends(get_db)):
    teacher = db.query(models.User).filter(models.User.id == id).first()
    if teacher:
        db.delete(teacher)
        db.commit()
    return RedirectResponse("/admin/teachers", status_code=302)


@app.get("/admin/students", response_class=HTMLResponse)
def admin_students(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    students = db.query(models.User).filter(models.User.role == "student").all()
    return render("student.html", request, {**user, "students": students})


@app.post("/admin/students/add")
def add_student(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if not existing:
        db.add(models.User(name=name, email=email, password=password, role="student"))
        db.commit()
    return RedirectResponse("/admin/students", status_code=302)


@app.post("/admin/students/delete/{id}")
def delete_student(id: int, db: Session = Depends(get_db)):
    student = db.query(models.User).filter(models.User.id == id).first()
    if student:
        db.delete(student)
        db.commit()
    return RedirectResponse("/admin/students", status_code=302)


@app.get("/admin/subjects", response_class=HTMLResponse)
def admin_subjects(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    assignments = db.query(models.Assignment).all()
    return render("assigments.html", request, {**user, "assignments": assignments})


@app.get("/admin/teacher-assign", response_class=HTMLResponse)
def admin_teacher_assign(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    teachers = db.query(models.User).filter(models.User.role == "teacher").all()
    assignments = db.query(models.Assignment).all()
    return render("assigment_sub.html", request, {**user, "teachers": teachers, "assignments": assignments})


@app.get("/admin/structure", response_class=HTMLResponse)
def admin_structure(request: Request):
    user = get_user_from_cookies(request)
    return render("course.html", request, user)


# =========================
# TEACHER ROUTES
# =========================
@app.get("/teacher/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request):
    user = get_user_from_cookies(request)
    return render("dashboard_t.html", request, user)


@app.get("/teacher/attendance", response_class=HTMLResponse)
def teacher_attendance(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    students = db.query(models.User).filter(models.User.role == "student").all()
    return render("teacher_attendence.html", request, {**user, "students": students})


@app.get("/teacher/notes", response_class=HTMLResponse)
def teacher_notes(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    notes = db.query(models.Note).all() if hasattr(models, 'Note') else []
    return render("notes.html", request, {**user, "notes": notes})


@app.get("/teacher/assignments", response_class=HTMLResponse)
def teacher_assignments(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    assignments = db.query(models.Assignment).all()
    return render("assigments.html", request, {**user, "assignments": assignments})


# =========================
# STUDENT ROUTES
# =========================
@app.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard(request: Request):
    user = get_user_from_cookies(request)
    return render("student_dashboard.html", request, user)


@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    assignments = db.query(models.Assignment).all()
    submissions = db.query(models.Submission).all()
    return render("assigments.html", request, {
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


@app.get("/student/attendance", response_class=HTMLResponse)
def student_attendance(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    return render("stu_attendence.html", request, user)


@app.get("/student/courses", response_class=HTMLResponse)
def student_courses(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    courses = db.query(models.Course).all() if hasattr(models, 'Course') else []
    return render("stu_course.html", request, {**user, "courses": courses})


@app.get("/student/notes", response_class=HTMLResponse)
def student_notes(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookies(request)
    notes = db.query(models.Note).all() if hasattr(models, 'Note') else []
    return render("stu_note.html", request, {**user, "notes": notes})


# =========================
# CATCH ALL — SABSE LAST MEIN
# =========================
@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return RedirectResponse("/")
