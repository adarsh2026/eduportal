from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
import os, shutil
import models
from database import get_db, engine

app = FastAPI(debug=True)
models.Base.metadata.create_all(bind=engine)

# ── Auto-migrate: add missing columns to existing DBs ──
from sqlalchemy import text as _text
def _safe_add_col(sql):
    from database import engine as _eng
    try:
        with _eng.connect() as _conn:
            _conn.execute(_text(sql))
            _conn.commit()
    except Exception:
        pass

_safe_add_col("ALTER TABLE assignments ADD COLUMN teacher_id INTEGER REFERENCES users(id)")
_safe_add_col("ALTER TABLE assignments ADD COLUMN section_id INTEGER")
_safe_add_col("ALTER TABLE notes ADD COLUMN section_id INTEGER")
_safe_add_col("ALTER TABLE notes ADD COLUMN semester_id INTEGER")
_safe_add_col("ALTER TABLE notes ADD COLUMN due_date TEXT")
_safe_add_col("ALTER TABLE notes ADD COLUMN filename TEXT")
# ──────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ══════════════════════════════════════════════════════
#  AUTH GUARDS  — call these at the top of each route
# ══════════════════════════════════════════════════════
def require_login(request: Request):
    """Redirect to login if no user_id cookie."""
    uid = 0
    try: uid = int(request.cookies.get("user_id", 0))
    except: pass
    if not uid:
        return RedirectResponse(url="/", status_code=302)
    return None

def require_role(request: Request, role: str):
    """Redirect to login if not logged in OR wrong role."""
    uid  = 0
    try: uid = int(request.cookies.get("user_id", 0))
    except: pass
    if not uid:
        return RedirectResponse(url="/", status_code=302)
    actual_role = request.cookies.get("user_role", "")
    if actual_role != role:
        # Wrong role → send to their own dashboard
        if actual_role in ("admin", "teacher", "student"):
            return RedirectResponse(url=f"/{actual_role}/dashboard", status_code=302)
        return RedirectResponse(url="/", status_code=302)
    return None

# ── Helpers ────────────────────────────────────────────
def get_user_id(request: Request) -> int:
    try:    return int(request.cookies.get("user_id", 0))
    except: return 0

def render(tpl: str, request: Request, ctx: dict = {}):
    data = {"request": request}
    data.update(ctx)
    return templates.TemplateResponse(request, tpl, data)

def get_teacher_assignments(tid: int, db: Session):
    tas = db.query(models.TeacherAssignment).filter(
        models.TeacherAssignment.teacher_id == tid).all()
    result = []
    for a in tas:
        subject  = db.query(models.Subject).filter(models.Subject.id == a.subject_id).first()
        section  = db.query(models.Section).filter(models.Section.id == a.section_id).first()
        semester = db.query(models.Semester).filter(models.Semester.id == a.semester_id).first()
        year     = db.query(models.AcademicYear).filter(models.AcademicYear.id == a.year_id).first()
        course   = db.query(models.AcademicCourse).filter(models.AcademicCourse.id == a.academic_course_id).first()
        if not all([subject, section, semester, year, course]):
            continue
        label = f"{course.code} Y{year.year_number} S{semester.semester_number} Sec-{section.name} — {subject.name}"
        result.append({
            "assignment_id": a.id, "subject_id": subject.id,
            "subject_name": subject.name, "subject_code": subject.code or "",
            "section_id": section.id, "section_name": section.name,
            "semester_id": semester.id, "semester_number": semester.semester_number,
            "year_id": year.id, "year_number": year.year_number,
            "course_id": course.id, "course_name": course.name, "course_code": course.code,
            "label": label,
        })
    return result

def get_student_section(sid: int, db: Session):
    return db.query(models.StudentSection).filter(
        models.StudentSection.student_id == sid).first()

# ── Cascade JSON APIs ──────────────────────────────────
@app.get("/api/years")
def api_years(course_id: int = 0, db: Session = Depends(get_db)):
    if not course_id: return JSONResponse([])
    rows = db.query(models.AcademicYear).filter(
        models.AcademicYear.course_id == course_id
    ).order_by(models.AcademicYear.year_number).all()
    return JSONResponse([{"id": y.id, "year_number": y.year_number} for y in rows])

@app.get("/api/semesters")
def api_semesters(year_id: int = 0, db: Session = Depends(get_db)):
    if not year_id: return JSONResponse([])
    rows = db.query(models.Semester).filter(
        models.Semester.year_id == year_id
    ).order_by(models.Semester.semester_number).all()
    return JSONResponse([{"id": s.id, "semester_number": s.semester_number} for s in rows])

@app.get("/api/sections")
def api_sections(semester_id: int = 0, db: Session = Depends(get_db)):
    if not semester_id: return JSONResponse([])
    rows = db.query(models.Section).filter(
        models.Section.semester_id == semester_id
    ).order_by(models.Section.name).all()
    return JSONResponse([{"id": s.id, "name": s.name} for s in rows])

@app.get("/api/subjects")
def api_subjects(semester_id: int = 0, db: Session = Depends(get_db)):
    if not semester_id: return JSONResponse([])
    rows = db.query(models.Subject).filter(
        models.Subject.semester_id == semester_id
    ).order_by(models.Subject.name).all()
    return JSONResponse([{"id": s.id, "name": s.name, "code": s.code or ""} for s in rows])

# ── AUTH ───────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return render("login.html", request, {"error": None})

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(func.lower(models.User.email) == email.strip().lower()).first()
    if not user or user.password.strip() != password.strip():
        return render("login.html", request, {"error": "Invalid email or password"})
    res = RedirectResponse(url=f"/{user.role}/dashboard", status_code=302)
    res.set_cookie("user_id",   str(user.id))
    res.set_cookie("user_role", user.role)
    res.set_cookie("user_name", user.name)
    return res

@app.get("/logout")
def logout():
    res = RedirectResponse(url="/", status_code=302)
    for c in ("user_id", "user_role", "user_name"): res.delete_cookie(c)
    return res

# ══ ADMIN ══════════════════════════════════════════════
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    return render("dashboard.html", request, {
        "teacher_count": db.query(models.User).filter(models.User.role == "teacher").count(),
        "student_count": db.query(models.User).filter(models.User.role == "student").count(),
        "course_count":  db.query(models.AcademicCourse).count(),
        "subject_count": db.query(models.Subject).count(),
        "section_count": db.query(models.Section).count(),
        "assign_count":  db.query(models.TeacherAssignment).count(),
        "user_name":     request.cookies.get("user_name", "Admin"),
    })

@app.get("/admin/teachers", response_class=HTMLResponse)
def admin_teachers(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    teachers    = db.query(models.User).filter(models.User.role == "teacher").all()
    courses     = db.query(models.AcademicCourse).all()
    assignments = db.query(models.TeacherAssignment).all()
    t_map   = {t.id: t for t in teachers}
    c_map   = {c.id: c for c in courses}
    y_map   = {y.id: y for y in db.query(models.AcademicYear).all()}
    s_map   = {s.id: s for s in db.query(models.Semester).all()}
    sec_map = {s.id: s for s in db.query(models.Section).all()}
    sub_map = {s.id: s for s in db.query(models.Subject).all()}
    enriched = []
    for a in assignments:
        t   = t_map.get(a.teacher_id)
        co  = c_map.get(a.academic_course_id)
        yr  = y_map.get(a.year_id)
        sem = s_map.get(a.semester_id)
        sec = sec_map.get(a.section_id)
        sub = sub_map.get(a.subject_id)
        enriched.append({
            "id": a.id, "teacher_name": t.name if t else "—",
            "course_code": co.code if co else "—", "course_name": co.name if co else "—",
            "year_number": yr.year_number if yr else "—",
            "sem_number":  sem.semester_number if sem else "—",
            "section_name": sec.name if sec else "—",
            "subject_name": sub.name if sub else "—",
            "subject_code": sub.code if sub else "",
        })
    return render("teachers.html", request, {
        "teachers":             teachers,
        "courses":              courses,
        "enriched_assignments": enriched,
        "user_name":            request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/teachers/add")
def add_teacher(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...),
                course_id: int = Form(0), year_id: int = Form(0), semester_id: int = Form(0),
                section_id: int = Form(0), subject_id: int = Form(0), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(400, "Email already exists")
    user = models.User(name=name, email=email, password=password, role="teacher")
    db.add(user); db.flush()
    if all([course_id, year_id, semester_id, section_id, subject_id]):
        if not db.query(models.TeacherAssignment).filter(
            models.TeacherAssignment.teacher_id == user.id,
            models.TeacherAssignment.section_id == section_id,
            models.TeacherAssignment.subject_id == subject_id).first():
            db.add(models.TeacherAssignment(
                teacher_id=user.id, academic_course_id=course_id,
                year_id=year_id, semester_id=semester_id,
                section_id=section_id, subject_id=subject_id))
    db.commit()
    return RedirectResponse("/admin/teachers", status_code=302)

@app.post("/admin/teachers/delete/{tid}")
def delete_teacher(request: Request, tid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    t = db.query(models.User).filter(models.User.id == tid).first()
    if t: db.delete(t); db.commit()
    return RedirectResponse("/admin/teachers", status_code=302)

@app.post("/admin/teachers/assign")
def assign_teacher_subject(request: Request, teacher_id: int = Form(...), course_id: int = Form(...),
    year_id: int = Form(...), semester_id: int = Form(...),
    section_id: int = Form(...), subject_id: int = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    if not db.query(models.TeacherAssignment).filter(
        models.TeacherAssignment.teacher_id == teacher_id,
        models.TeacherAssignment.section_id == section_id,
        models.TeacherAssignment.subject_id == subject_id).first():
        db.add(models.TeacherAssignment(
            teacher_id=teacher_id, academic_course_id=course_id,
            year_id=year_id, semester_id=semester_id,
            section_id=section_id, subject_id=subject_id))
        db.commit()
    return RedirectResponse("/admin/teachers", status_code=302)

@app.post("/admin/teachers/assignment/delete/{aid}")
def delete_ta(request: Request, aid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    a = db.query(models.TeacherAssignment).filter(models.TeacherAssignment.id == aid).first()
    if a: db.delete(a); db.commit()
    return RedirectResponse("/admin/teachers", status_code=302)

@app.get("/admin/students", response_class=HTMLResponse)
def admin_students(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    students  = db.query(models.User).filter(models.User.role == "student").all()
    courses   = db.query(models.AcademicCourse).all()
    ss_list   = db.query(models.StudentSection).all()
    ss_map    = {ss.student_id: ss for ss in ss_list}
    c_map     = {c.id: c for c in courses}
    y_map     = {y.id: y for y in db.query(models.AcademicYear).all()}
    sem_map   = {s.id: s for s in db.query(models.Semester).all()}
    sec_map   = {s.id: s for s in db.query(models.Section).all()}
    enriched  = []
    for s in students:
        ss  = ss_map.get(s.id)
        co  = c_map.get(ss.course_id)    if ss else None
        yr  = y_map.get(ss.year_id)      if ss else None
        sem = sem_map.get(ss.semester_id) if ss else None
        sec = sec_map.get(ss.section_id)  if ss else None
        enriched.append({
            "student":      s,
            "course_code":  co.code if co else None,
            "year_number":  yr.year_number if yr else None,
            "sem_number":   sem.semester_number if sem else None,
            "section_name": sec.name if sec else None,
        })
    return render("student.html", request, {
        "enriched_students": enriched,
        "courses":           courses,
        "user_name":         request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/students/add")
def add_student(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...),
                course_id: int = Form(0), year_id: int = Form(0),
                semester_id: int = Form(0), section_id: int = Form(0),
                db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(400, "Email already exists")
    user = models.User(name=name, email=email, password=password, role="student")
    db.add(user); db.flush()
    if all([course_id, year_id, semester_id, section_id]):
        db.add(models.StudentSection(
            student_id=user.id, section_id=section_id,
            semester_id=semester_id, year_id=year_id, course_id=course_id))
    db.commit()
    return RedirectResponse("/admin/students", status_code=302)

@app.post("/admin/students/delete/{sid}")
def delete_student(request: Request, sid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    s = db.query(models.User).filter(models.User.id == sid).first()
    if s:
        db.query(models.StudentSection).filter(models.StudentSection.student_id == sid).delete()
        db.delete(s); db.commit()
    return RedirectResponse("/admin/students", status_code=302)

@app.post("/admin/students/assign-section")
def reassign_student_section(request: Request,
    student_id: int = Form(...), course_id: int = Form(...), year_id: int = Form(...),
    semester_id: int = Form(...), section_id: int = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    ex = db.query(models.StudentSection).filter(
        models.StudentSection.student_id == student_id).first()
    if ex:
        ex.course_id = course_id; ex.year_id = year_id
        ex.semester_id = semester_id; ex.section_id = section_id
    else:
        db.add(models.StudentSection(
            student_id=student_id, course_id=course_id, year_id=year_id,
            semester_id=semester_id, section_id=section_id))
    db.commit()
    return RedirectResponse("/admin/students", status_code=302)

@app.get("/admin/academic-courses", response_class=HTMLResponse)
def admin_academic_courses(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    return render("admin_courses.html", request, {
        "courses":   db.query(models.AcademicCourse).all(),
        "user_name": request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/academic-courses/add")
def add_academic_course(request: Request, name: str = Form(...), code: str = Form(...),
    duration_years: int = Form(3), description: str = Form(""), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    db.add(models.AcademicCourse(name=name, code=code.upper(),
        duration_years=duration_years, description=description))
    db.commit()
    return RedirectResponse("/admin/academic-courses", status_code=302)

@app.post("/admin/academic-courses/delete/{cid}")
def delete_academic_course(request: Request, cid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    c = db.query(models.AcademicCourse).filter(models.AcademicCourse.id == cid).first()
    if c: db.delete(c); db.commit()
    return RedirectResponse("/admin/academic-courses", status_code=302)

@app.get("/admin/structure", response_class=HTMLResponse)
def admin_structure(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    courses   = db.query(models.AcademicCourse).all()
    years     = db.query(models.AcademicYear).all()
    semesters = db.query(models.Semester).all()
    sections  = db.query(models.Section).all()
    return render("admin_structure.html", request, {
        "courses": courses, "years": years, "semesters": semesters, "sections": sections,
        "course_map":   {c.id: c for c in courses},
        "year_map":     {y.id: y for y in years},
        "semester_map": {s.id: s for s in semesters},
        "user_name":    request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/years/add")
def add_year(request: Request, course_id: int = Form(...), year_number: int = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    if not db.query(models.AcademicYear).filter(
        models.AcademicYear.course_id == course_id,
        models.AcademicYear.year_number == year_number).first():
        db.add(models.AcademicYear(course_id=course_id, year_number=year_number)); db.commit()
    return RedirectResponse("/admin/structure", status_code=302)

@app.post("/admin/years/delete/{yid}")
def delete_year(request: Request, yid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    y = db.query(models.AcademicYear).filter(models.AcademicYear.id == yid).first()
    if y: db.delete(y); db.commit()
    return RedirectResponse("/admin/structure", status_code=302)

@app.post("/admin/semesters/add")
def add_semester(request: Request, year_id: int = Form(...), semester_number: int = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    if not db.query(models.Semester).filter(
        models.Semester.year_id == year_id,
        models.Semester.semester_number == semester_number).first():
        db.add(models.Semester(year_id=year_id, semester_number=semester_number)); db.commit()
    return RedirectResponse("/admin/structure", status_code=302)

@app.post("/admin/semesters/delete/{sid}")
def delete_semester(request: Request, sid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    s = db.query(models.Semester).filter(models.Semester.id == sid).first()
    if s: db.delete(s); db.commit()
    return RedirectResponse("/admin/structure", status_code=302)

@app.post("/admin/sections/add")
def add_section(request: Request, semester_id: int = Form(...), name: str = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    if not db.query(models.Section).filter(
        models.Section.semester_id == semester_id,
        models.Section.name == name.upper()).first():
        db.add(models.Section(semester_id=semester_id, name=name.upper())); db.commit()
    return RedirectResponse("/admin/structure", status_code=302)

@app.post("/admin/sections/delete/{sid}")
def delete_section(request: Request, sid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    s = db.query(models.Section).filter(models.Section.id == sid).first()
    if s: db.delete(s); db.commit()
    return RedirectResponse("/admin/structure", status_code=302)

@app.get("/admin/subjects", response_class=HTMLResponse)
def admin_subjects(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    courses = db.query(models.AcademicCourse).all()
    years   = db.query(models.AcademicYear).all()
    sems    = db.query(models.Semester).all()
    return render("admin_subjects.html", request, {
        "subjects": db.query(models.Subject).all(), "courses": courses,
        "years": years, "semesters": sems,
        "course_map":   {c.id: c for c in courses},
        "year_map":     {y.id: y for y in years},
        "semester_map": {s.id: s for s in sems},
        "user_name":    request.cookies.get("user_name", "Admin"),
    })

@app.post("/admin/subjects/add")
def add_subject(request: Request, semester_id: int = Form(...), name: str = Form(...), code: str = Form(""), db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    db.add(models.Subject(semester_id=semester_id, name=name, code=code.upper())); db.commit()
    return RedirectResponse("/admin/subjects", status_code=302)

@app.post("/admin/subjects/delete/{sid}")
def delete_subject(request: Request, sid: int, db: Session = Depends(get_db)):
    guard = require_role(request, "admin")
    if guard: return guard
    s = db.query(models.Subject).filter(models.Subject.id == sid).first()
    if s: db.delete(s); db.commit()
    return RedirectResponse("/admin/subjects", status_code=302)

@app.get("/admin/assignments")
def admin_assignments_redirect():
    return RedirectResponse("/admin/teachers", status_code=302)

# ══ TEACHER ════════════════════════════════════════════
@app.get("/teacher/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    tid = get_user_id(request)
    assignments = get_teacher_assignments(tid, db)
    return render("dashboard_t.html", request, {
        "subject_count":    len(set(a["subject_id"] for a in assignments)),
        "section_count":    len(set(a["section_id"] for a in assignments)),
        "assignment_count": len(assignments),
        "assignments":      assignments,
        "user_name":        request.cookies.get("user_name", "Teacher"),
    })

@app.get("/teacher/notes", response_class=HTMLResponse)
def teacher_notes(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    tid = get_user_id(request)
    assignments = get_teacher_assignments(tid, db)
    notes = db.query(models.Note).filter(models.Note.teacher_id == tid).all()
    sub_map = {a["subject_id"]: a for a in assignments}
    enriched_notes = []
    for n in notes:
        a   = sub_map.get(n.course_id)
        lbl = a["label"] if a else f"Subject #{n.course_id}"
        enriched_notes.append({"note": n, "label": lbl})
    return render("notes.html", request, {
        "assignments":    assignments,
        "enriched_notes": enriched_notes,
        "user_name":      request.cookies.get("user_name", "Teacher"),
    })

@app.post("/teacher/notes/add")
async def upload_note(request: Request, title: str = Form(...),
    assignment_key: str = Form(...), file: UploadFile = File(None), db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    tid   = get_user_id(request)
    parts = assignment_key.split(":")
    subject_id  = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    section_id  = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    semester_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    filename = None
    try:
        if file and file.filename:
            ext = os.path.splitext(file.filename)[1]
            filename = f"note_{tid}_{int(datetime.now().timestamp())}{ext}"
            with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
                shutil.copyfileobj(file.file, f)
    except Exception:
        pass
    try:
        note = models.Note(title=title, content="", course_id=subject_id,
            teacher_id=tid, filename=filename,
            section_id=section_id, semester_id=semester_id)
        db.add(note); db.commit()
    except Exception:
        db.rollback()
        note = models.Note(title=title, content="", course_id=subject_id,
            teacher_id=tid, filename=filename)
        db.add(note); db.commit()
    return RedirectResponse("/teacher/notes", status_code=302)

@app.get("/teacher/assignments", response_class=HTMLResponse)
def teacher_assignments(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    tid = get_user_id(request)
    ta_assignments = get_teacher_assignments(tid, db)
    try:
        hw_assignments = db.query(models.Assignment).filter(models.Assignment.teacher_id == tid).all()
    except Exception:
        db.rollback()
        hw_assignments = db.query(models.Assignment).all()
    assign_ids  = [int(a.id) for a in hw_assignments]
    raw_subs    = db.query(models.Submission).filter(
        models.Submission.assignment_id.in_(assign_ids)).all() if assign_ids else []
    student_map = {u.id: u.name for u in db.query(models.User).filter(models.User.role == "student").all()}
    assign_map  = {int(a.id): a.title for a in hw_assignments}
    sub_map     = {a["subject_id"]: a for a in ta_assignments}
    class E: pass
    enriched = []
    for s in raw_subs:
        e = E()
        e.id = s.id; e.assignment_id = s.assignment_id; e.student_id = s.student_id
        e.answer = s.answer; e.submitted_at = s.submitted_at
        e.student_name     = student_map.get(int(s.student_id), f"Student #{s.student_id}")
        e.assignment_title = assign_map.get(int(s.assignment_id), f"Assignment #{s.assignment_id}")
        enriched.append(e)
    enriched_hw = []
    for a in hw_assignments:
        ta  = sub_map.get(a.course_id)
        lbl = ta["label"] if ta else f"Subject #{a.course_id}"
        enriched_hw.append({"assignment": a, "label": lbl})
    return render("assignments.html", request, {
        "enriched_hw":    enriched_hw,
        "ta_assignments": ta_assignments,
        "submissions":    enriched,
        "user_name":      request.cookies.get("user_name", "Teacher"),
    })

@app.post("/teacher/assignments/add")
def create_assignment(request: Request, title: str = Form(...),
    assignment_key: str = Form(...), description: str = Form(""),
    due_date: str = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    parts = assignment_key.split(":")
    subject_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    section_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    tid = get_user_id(request)
    try:
        db.add(models.Assignment(title=title, description=description, due_date=due_date,
            course_id=subject_id, section_id=section_id, teacher_id=tid))
        db.commit()
    except Exception:
        db.rollback()
        db.add(models.Assignment(title=title, description=description, due_date=due_date,
            course_id=subject_id, section_id=section_id))
        db.commit()
    return RedirectResponse("/teacher/assignments", status_code=302)

@app.get("/teacher/attendance", response_class=HTMLResponse)
def teacher_attendance(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    tid = get_user_id(request)
    assignments = get_teacher_assignments(tid, db)
    section_ids = list(set(a["section_id"] for a in assignments))
    ss_records  = db.query(models.StudentSection).filter(
        models.StudentSection.section_id.in_(section_ids)).all() if section_ids else []
    student_ids = [ss.student_id for ss in ss_records]
    students    = db.query(models.User).filter(models.User.id.in_(student_ids)).all() if student_ids else []
    return render("teacher_attendence.html", request, {
        "assignments": assignments,
        "students":    students,
        "today":       date.today().isoformat(),
        "user_name":   request.cookies.get("user_name", "Teacher"),
    })

@app.post("/teacher/attendance/mark")
async def mark_attendance(request: Request, subject_id: int = Form(...),
    section_id: int = Form(...), date: str = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    tid = get_user_id(request)
    ta  = db.query(models.TeacherAssignment).filter(
        models.TeacherAssignment.teacher_id == tid,
        models.TeacherAssignment.subject_id == subject_id,
        models.TeacherAssignment.section_id == section_id).first()
    if not ta:
        return RedirectResponse("/teacher/attendance", status_code=302)
    form = await request.form()
    student_ids = form.getlist("student_ids")
    for sid in student_ids:
        sv = form.get(f"status_{sid}", "absent")
        ex = db.query(models.Attendance).filter(
            models.Attendance.student_id == int(sid),
            models.Attendance.subject_id == subject_id,
            models.Attendance.section_id == section_id,
            models.Attendance.date       == date).first()
        if ex: ex.status = sv
        else:
            db.add(models.Attendance(subject_id=subject_id, section_id=section_id,
                student_id=int(sid), date=date, status=sv))
    db.commit()
    return RedirectResponse("/teacher/attendance", status_code=302)

@app.get("/teacher/attendance/view")
def view_attendance(request: Request, subject_id: int = 0, section_id: int = 0,
    date: str = "", db: Session = Depends(get_db)):
    guard = require_role(request, "teacher")
    if guard: return guard
    tid = get_user_id(request)
    ta  = db.query(models.TeacherAssignment).filter(
        models.TeacherAssignment.teacher_id == tid,
        models.TeacherAssignment.subject_id == subject_id,
        models.TeacherAssignment.section_id == section_id).first()
    if not ta:
        return JSONResponse({"records": []})
    q = db.query(models.Attendance).filter(
        models.Attendance.subject_id == subject_id,
        models.Attendance.section_id == section_id)
    if date:
        q = q.filter(models.Attendance.date == date)
    recs     = q.order_by(models.Attendance.date.desc()).all()
    students = {u.id: u.name for u in db.query(models.User).filter(models.User.role == "student").all()}
    data = [{"student_id": r.student_id,
             "student_name": students.get(r.student_id, f"#{r.student_id}"),
             "date": r.date, "status": r.status} for r in recs]
    return JSONResponse({"records": data})

@app.get("/teacher/attendance/filter")
def filter_attendance(request: Request, subject_id: int = 0, section_id: int = 0,
    date: str = "", db: Session = Depends(get_db)):
    return view_attendance(request=request, subject_id=subject_id,
        section_id=section_id, date=date, db=db)

# ══ STUDENT ════════════════════════════════════════════
@app.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "student")
    if guard: return guard
    sid  = get_user_id(request)
    ss   = get_student_section(sid, db)
    recs = db.query(models.Attendance).filter(models.Attendance.student_id == sid).all()
    present = sum(1 for r in recs if r.status == "present")
    total   = len(recs)
    note_count = assignment_count = 0
    if ss:
        note_count       = db.query(models.Note).filter(
            models.Note.semester_id == ss.semester_id,
            models.Note.section_id  == ss.section_id).count()
        assignment_count = db.query(models.Assignment).filter(
            models.Assignment.section_id == ss.section_id).count()
    return render("student_dashboard.html", request, {
        "note_count":       note_count,
        "assignment_count": assignment_count,
        "submission_count": db.query(models.Submission).filter(
            models.Submission.student_id == sid).count(),
        "attendance_pct":   int((present / total) * 100) if total else 0,
        "user_name":        request.cookies.get("user_name", "Student"),
        "section_info":     ss,
    })

@app.get("/student/notes", response_class=HTMLResponse)
def student_notes(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "student")
    if guard: return guard
    sid  = get_user_id(request)
    ss   = get_student_section(sid, db)
    notes = []
    if ss:
        notes = db.query(models.Note).filter(
            models.Note.semester_id == ss.semester_id,
            models.Note.section_id  == ss.section_id).all()
    subject_map = {s.id: s.name for s in db.query(models.Subject).all()}
    enriched = [{"note": n, "subject_name": subject_map.get(n.course_id, f"Subject #{n.course_id}")} for n in notes]
    return render("stu_note.html", request, {
        "enriched_notes": enriched,
        "user_name":      request.cookies.get("user_name", "Student"),
    })

@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "student")
    if guard: return guard
    sid  = get_user_id(request)
    ss   = get_student_section(sid, db)
    assignments = []
    if ss:
        assignments = db.query(models.Assignment).filter(
            models.Assignment.section_id == ss.section_id).all()
    raw_subs    = db.query(models.Submission).filter(models.Submission.student_id == sid).all()
    submissions = {}
    for s in raw_subs:
        try: submissions[int(s.assignment_id)] = s
        except: pass
    subject_map = {s.id: s.name for s in db.query(models.Subject).all()}
    return render("assigment_sub.html", request, {
        "assignments": assignments,
        "submissions": submissions,
        "subject_map": subject_map,
        "user_name":   request.cookies.get("user_name", "Student"),
    })

@app.post("/student/assignments/submit")
def submit_assignment(request: Request, assignment_id: int = Form(...),
    answer: str = Form(...), db: Session = Depends(get_db)):
    guard = require_role(request, "student")
    if guard: return guard
    sid = get_user_id(request)
    if not db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment_id,
        models.Submission.student_id    == sid).first():
        db.add(models.Submission(assignment_id=assignment_id, student_id=sid,
            answer=answer, submitted_at=datetime.now().strftime("%Y-%m-%d %H:%M")))
        db.commit()
    return RedirectResponse("/student/assignments", status_code=302)

@app.get("/student/attendance", response_class=HTMLResponse)
def student_attendance(request: Request, db: Session = Depends(get_db)):
    guard = require_role(request, "student")
    if guard: return guard
    sid  = get_user_id(request)
    ss   = get_student_section(sid, db)
    recs = db.query(models.Attendance).filter(
        models.Attendance.student_id == sid).order_by(models.Attendance.date.desc()).all()
    present = sum(1 for r in recs if r.status == "present")
    total   = len(recs)
    subject_map = {s.id: s.name for s in db.query(models.Subject).all()}
    return render("stu_attendence.html", request, {
        "records":      recs,
        "present":      present,
        "absent":       total - present,
        "total":        total,
        "pct":          int((present / total) * 100) if total else 0,
        "course_map":   subject_map,
        "section_info": ss,
        "user_name":    request.cookies.get("user_name", "Student"),
        "today":        date.today().isoformat(),
    })