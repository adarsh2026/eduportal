from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date

import models
from database import get_db, engine

app = FastAPI(debug=True)

# 🔥 FIX: database tables auto create
models.Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── HELPER ────────────────────────────────────────────────────────────────
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

# ── AUTH ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return render("login.html", request, {"error": None})

@app.post("/login")
def login(
    request:  Request,
    email:    str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    email = email.strip()
    password = password.strip()

    user = db.query(models.User).filter(
        func.lower(models.User.email) == email.lower()
    ).first()

    if not user or user.password.strip() != password:
        return render("login.html", request, {"error": "Invalid email or password"})

    response = RedirectResponse(url=f"/{user.role}/dashboard", status_code=302)
    response.set_cookie("user_id",   str(user.id))
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


# ── ADMIN ────────────────────────────────────────────────────────────────

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    return render("dashboard.html", request, {
        "teacher_count": db.query(models.User).filter(models.User.role == "teacher").count(),
        "student_count": db.query(models.User).filter(models.User.role == "student").count(),
        "course_count":  db.query(models.Course).count(),
        "user_name":     request.cookies.get("user_name", "Admin"),
    })

@app.get("/admin/teachers", response_class=HTMLResponse)
def admin_teachers(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    return render("teachers.html", request, {
        "teachers":  db.query(models.User).filter(models.User.role == "teacher").all(),
        "user_name": request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/teachers/add")
def add_teacher(
    request: Request,
    name:     str = Form(...),
    email:    str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
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
        "students":  db.query(models.User).filter(models.User.role == "student").all(),
        "user_name": request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/students/add")
def add_student(
    request: Request,
    name:     str = Form(...),
    email:    str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    db.add(models.User(name=name, email=email, password=password, role="student"))
    db.commit()
    return RedirectResponse(url="/admin/students", status_code=302)

@app.post("/admin/students/delete/{student_id}")
def delete_student(request: Request, student_id: int, db: Session = Depends(get_db)):
    if not require_role(request, "admin"):
        return RedirectResponse("/", status_code=302)

    s = db.query(models.User).filter(models.User.id == student_id).first()
    if s:
        db.delete(s)
        db.commit()
    return RedirectResponse(url="/admin/students", status_code=302)

# ── TEACHER ────────────────────────────────────────────────────────────────

@app.get("/teacher/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    return render("dashboard_t.html", request, {
        "course_count":     db.query(models.Course).filter(models.Course.teacher_id == tid).count(),
        "assignment_count": db.query(models.Assignment).filter(models.Assignment.teacher_id == tid).count(),
        "user_name":        request.cookies.get("user_name", "Teacher"),
    })

@app.get("/teacher/courses", response_class=HTMLResponse)
def teacher_courses(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    return render("course.html", request, {
        "courses":   db.query(models.Course).filter(models.Course.teacher_id == tid).all(),
        "user_name": request.cookies.get("user_name", "Teacher"),
    })

@app.post("/teacher/courses/add")
def create_course(
    request:     Request,
    name:        str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    db.add(models.Course(name=name, description=description, teacher_id=tid))
    db.commit()
    return RedirectResponse(url="/teacher/courses", status_code=302)

@app.get("/teacher/notes", response_class=HTMLResponse)
def teacher_notes(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    return render("notes.html", request, {
        "courses":   db.query(models.Course).filter(models.Course.teacher_id == tid).all(),
        "notes":     db.query(models.Note).filter(models.Note.teacher_id == tid).all(),
        "user_name": request.cookies.get("user_name", "Teacher"),
    })

@app.post("/teacher/notes/add")
def upload_note(
    request:   Request,
    title:     str = Form(...),
    course_id: int = Form(...),
    content:   str = Form(...),
    db: Session = Depends(get_db)
):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    db.add(models.Note(title=title, content=content, course_id=course_id, teacher_id=tid))
    db.commit()
    return RedirectResponse(url="/teacher/notes", status_code=302)

@app.get("/teacher/assignments", response_class=HTMLResponse)
def teacher_assignments(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    return render("assigment.html", request, {
        "assignments": db.query(models.Assignment).filter(models.Assignment.teacher_id == tid).all(),
        "courses":     db.query(models.Course).filter(models.Course.teacher_id == tid).all(),
        "user_name":   request.cookies.get("user_name", "Teacher"),
    })

@app.post("/teacher/assignments/add")
def create_assignment(
    request:     Request,
    title:       str = Form(...),
    course_id:   int = Form(...),
    description: str = Form(""),
    due_date:    str = Form(...),
    db: Session = Depends(get_db)
):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    db.add(models.Assignment(
        title=title,
        description=description,
        due_date=due_date,
        course_id=course_id,
        teacher_id=tid
    ))
    db.commit()
    return RedirectResponse(url="/teacher/assignments", status_code=302)

@app.get("/teacher/attendance", response_class=HTMLResponse)
def teacher_attendance(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    tid = get_user_id(request)
    return render("teacher_attendence.html", request, {
        "courses":   db.query(models.Course).filter(models.Course.teacher_id == tid).all(),
        "students":  db.query(models.User).filter(models.User.role == "student").all(),
        "records":   db.query(models.Attendance).all(),
        "today":     date.today().isoformat(),
        "user_name": request.cookies.get("user_name", "Teacher"),
    })

@app.post("/teacher/attendance/mark")
def mark_attendance(
    request:    Request,
    course_id:  int = Form(...),
    student_id: int = Form(...),
    date:       str = Form(...),
    status_val: str = Form(...),
    db: Session = Depends(get_db)
):
    if not require_role(request, "teacher"):
        return RedirectResponse("/", status_code=302)

    existing = db.query(models.Attendance).filter(
        models.Attendance.student_id == student_id,
        models.Attendance.course_id  == course_id,
        models.Attendance.date       == date
    ).first()

    if existing:
        existing.status = status_val
    else:
        db.add(models.Attendance(
            course_id=course_id,
            student_id=student_id,
            date=date,
            status=status_val
        ))

    db.commit()
    return RedirectResponse(url="/teacher/attendance", status_code=302)

# ── STUDENT ────────────────────────────────────────────────────────────────

@app.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    sid     = get_user_id(request)
    records = db.query(models.Attendance).filter(models.Attendance.student_id == sid).all()
    present = sum(1 for r in records if r.status == "present")
    total   = len(records)
    att_pct = int((present / total) * 100) if total > 0 else 0

    return render("student_dashboard.html", request, {
        "course_count":     db.query(models.Course).count(),
        "submission_count": db.query(models.Submission).filter(models.Submission.student_id == sid).count(),
        "attendance_pct":   att_pct,
        "user_name":        request.cookies.get("user_name", "Student"),
    })

@app.get("/student/courses", response_class=HTMLResponse)
def student_courses(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    return render("stu_course.html", request, {
        "courses":   db.query(models.Course).all(),
        "user_name": request.cookies.get("user_name", "Student"),
    })

@app.get("/student/notes", response_class=HTMLResponse)
def student_notes(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    return render("stu_note.html", request, {
        "notes":     db.query(models.Note).all(),
        "user_name": request.cookies.get("user_name", "Student"),
    })

@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    sid         = get_user_id(request)
    assignments = db.query(models.Assignment).all()
    subs        = db.query(models.Submission).filter(models.Submission.student_id == sid).all()
    submissions = {s.assignment_id: s for s in subs}

    return render("assigment_sub.html", request, {
        "assignments": assignments,
        "submissions": submissions,
        "user_name":   request.cookies.get("user_name", "Student"),
    })

@app.post("/student/assignments/submit")
def submit_assignment(
    request:       Request,
    assignment_id: int = Form(...),
    answer:        str = Form(...),
    db: Session = Depends(get_db)
):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    sid      = get_user_id(request)
    existing = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment_id,
        models.Submission.student_id    == sid
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

@app.get("/student/attendance", response_class=HTMLResponse)
def student_attendance(request: Request, db: Session = Depends(get_db)):
    if not require_role(request, "student"):
        return RedirectResponse("/", status_code=302)

    sid     = get_user_id(request)
    records = db.query(models.Attendance).filter(models.Attendance.student_id == sid).all()
    present = sum(1 for r in records if r.status == "present")
    total   = len(records)
    pct     = int((present / total) * 100) if total > 0 else 0

    return render("stu_attendence.html", request, {
        "records": records,
        "present": present,
        "total":   total,
        "pct":     pct,
        "user_name": request.cookies.get("user_name", "Student"),
    })