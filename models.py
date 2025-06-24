from __future__ import annotations

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db: SQLAlchemy = SQLAlchemy()

# ─────────────────────────────  MODELS  ───────────────────────────────
class User(db.Model, UserMixin):  # type: ignore[misc]
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="parent")  # teacher | parent


class Student(db.Model):  # type: ignore[misc]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("user.id"))


class Song(db.Model):  # type: ignore[misc]
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    difficulty = db.Column(db.Integer, default=1)  # 1–4 ★


class Attendance(db.Model):  # type: ignore[misc]
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    date = db.Column(db.Date, nullable=False)
    __table_args__ = (UniqueConstraint("student_id", "date", name="uix_student_date"),)


class StudentSong(db.Model):  # type: ignore[misc]
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey("song.id"), primary_key=True)
