from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String)
    email    = Column(String, unique=True, index=True)
    password = Column(String)
    role     = Column(String)

class AcademicCourse(Base):
    __tablename__ = "academic_courses"
    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String)
    code           = Column(String)
    duration_years = Column(Integer, default=3)
    description    = Column(Text, default="")

class AcademicYear(Base):
    __tablename__ = "academic_years"
    id          = Column(Integer, primary_key=True, index=True)
    course_id   = Column(Integer, ForeignKey("academic_courses.id"))
    year_number = Column(Integer)

class Semester(Base):
    __tablename__ = "semesters"
    id              = Column(Integer, primary_key=True, index=True)
    year_id         = Column(Integer, ForeignKey("academic_years.id"))
    semester_number = Column(Integer)

class Section(Base):
    __tablename__ = "sections"
    id          = Column(Integer, primary_key=True, index=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    name        = Column(String)

class Subject(Base):
    __tablename__ = "subjects"
    id          = Column(Integer, primary_key=True, index=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    name        = Column(String)
    code        = Column(String, default="")

class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"
    id                 = Column(Integer, primary_key=True, index=True)
    teacher_id         = Column(Integer, ForeignKey("users.id"))
    academic_course_id = Column(Integer, ForeignKey("academic_courses.id"))
    year_id            = Column(Integer, ForeignKey("academic_years.id"))
    semester_id        = Column(Integer, ForeignKey("semesters.id"))
    section_id         = Column(Integer, ForeignKey("sections.id"))
    subject_id         = Column(Integer, ForeignKey("subjects.id"))

class StudentSection(Base):
    __tablename__ = "student_sections"
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("users.id"), unique=True)
    course_id   = Column(Integer, ForeignKey("academic_courses.id"))
    year_id     = Column(Integer, ForeignKey("academic_years.id"))
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    section_id  = Column(Integer, ForeignKey("sections.id"))

class Note(Base):
    __tablename__ = "notes"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String)
    content     = Column(Text, default="")
    filename    = Column(String, default=None)
    due_date    = Column(String, default=None)
    course_id   = Column(Integer, default=None)   # NO ForeignKey — stores subject_id
    section_id  = Column(Integer, default=None)
    semester_id = Column(Integer, default=None)
    teacher_id  = Column(Integer, ForeignKey("users.id"))

class Assignment(Base):
    __tablename__ = "assignments"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String)
    description = Column(Text, default="")
    due_date    = Column(String)
    course_id   = Column(Integer, default=None)   # NO ForeignKey — stores subject_id
    section_id  = Column(Integer, default=None)
    teacher_id  = Column(Integer, ForeignKey("users.id"))

class Submission(Base):
    __tablename__ = "submissions"
    id            = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id    = Column(Integer, ForeignKey("users.id"))
    answer        = Column(Text)
    submitted_at  = Column(String)

class Attendance(Base):
    __tablename__ = "attendance"
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, default=None)
    section_id = Column(Integer, default=None)
    date       = Column(String)
    status     = Column(String)