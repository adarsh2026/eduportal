from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String(100), nullable=False)
    email    = Column(String(150), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role     = Column(String(20), nullable=False)  # admin / teacher / student

class Course(Base):
    __tablename__ = "courses"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), nullable=False)
    description = Column(Text)
    teacher_id  = Column(Integer, ForeignKey("users.id"))

class Note(Base):
    __tablename__ = "notes"
    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String(200), nullable=False)
    content    = Column(Text, nullable=False)
    course_id  = Column(Integer, ForeignKey("courses.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))

class Assignment(Base):
    __tablename__ = "assignments"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    due_date    = Column(String(30))
    course_id   = Column(Integer, ForeignKey("courses.id"))
    teacher_id  = Column(Integer, ForeignKey("users.id"))

class Submission(Base):
    __tablename__ = "submissions"
    id            = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id    = Column(Integer, ForeignKey("users.id"))
    answer        = Column(Text)
    submitted_at  = Column(String(30))

class Attendance(Base):
    __tablename__ = "attendance"
    id         = Column(Integer, primary_key=True, index=True)
    course_id  = Column(Integer, ForeignKey("courses.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    date       = Column(String(20))
    status     = Column(String(10))  # present / absent