from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import os

import models
from database import get_db, engine

app = FastAPI()

# Static + templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# DB init
@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=engine)

# Home route
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# ===============================
# STUDENT ASSIGNMENTS (FIXED)
# ===============================
@app.get("/student/assignments", response_class=HTMLResponse)
def student_assignments(request: Request, db: Session = Depends(get_db)):

    assignments = db.query(models.Assignment).all()
    submissions_list = db.query(models.Submission).all()

    # ✅ FINAL FIX (tuple/dict issue solve)
    submissions = {}
    for s in submissions_list:
        try:
            key = int(s.assignment_id)
        except:
            key = int(s.assignment_id[0]) if isinstance(s.assignment_id, tuple) else int(s.assignment_id)

        submissions[key] = s

    return templates.TemplateResponse(
        "assignment.html",
        {
            "request": request,
            "assignments": assignments,
            "submissions": submissions
        }
    )


# ===============================
# SUBMIT ASSIGNMENT
# ===============================
@app.post("/student/assignments/submit")
def submit_assignment(
    assignment_id: int = Form(...),
    answer: str = Form(...),
    db: Session = Depends(get_db)
):

    sub = models.Submission(
        assignment_id=assignment_id,
        answer=answer,
        submitted_at=datetime.now()
    )

    db.add(sub)
    db.commit()

    return RedirectResponse("/student/assignments", status_code=302)