1 from flask_sqlalchemy import SQLAlchemy
 2 from flask_login import UserMixin
 3 from sqlalchemy import UniqueConstraint
 4 
 5 db = SQLAlchemy()
 6 
 7 class User(db.Model, UserMixin):
 8     id = db.Column(db.Integer, primary_key=True)
 9     email = db.Column(db.String, unique=True, nullable=False)
10     password = db.Column(db.String, nullable=False)
11     role = db.Column(db.String, default="parent")  # teacher | parent
12 
13 class Student(db.Model):
14     id = db.Column(db.Integer, primary_key=True)
15     name = db.Column(db.String, nullable=False)
16     parent_id = db.Column(db.Integer, db.ForeignKey("user.id"))
17 
18 class Song(db.Model):
19     id = db.Column(db.Integer, primary_key=True)
20     title = db.Column(db.String, nullable=False)
21     author = db.Column(db.String, nullable=False)
22     difficulty = db.Column(db.Integer, default=1)  # 1–4 ★
23 
24 class Attendance(db.Model):
25     id = db.Column(db.Integer, primary_key=True)
26     student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
27     date = db.Column(db.Date, nullable=False)
28     __table_args__ = (UniqueConstraint("student_id", "date", name="unique_attendance"),)
29 
30 class StudentSong(db.Model):
31     student_id = db.Column(db.Integer, db.ForeignKey("student.id"), primary_key=True)
32     song_id = db.Column(db.Integer, db.ForeignKey("song.id"), primary_key=True)
