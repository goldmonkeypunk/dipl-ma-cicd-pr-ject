from __future__ import annotations

import calendar
import datetime as dt
import logging
from pathlib import Path
from typing import Dict, List, Set

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import LoginManager, current_user, login_required
from sqlalchemy import delete
from werkzeug.security import generate_password_hash
from werkzeug.wrappers.response import Response

from models import Attendance, Song, Student, StudentSong, User, db

PRICE: int = 130
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATA_DIR / 'app.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "CHANGE_ME_IN_PROD"

db.init_app(app)

login = LoginManager(app)
login.login_view = "auth.login"


@login.user_loader
def load_user(uid: str) -> User | None:
    return db.session.get(User, int(uid))


from auth import bp as auth_bp  # noqa: E402

app.register_blueprint(auth_bp)


def month_info(
    year: int, month: int
) -> tuple[list[dt.date], dt.date, dt.date]:
    days_cnt = calendar.monthrange(year, month)[1]
    dates = [dt.date(year, month, d) for d in range(1, days_cnt + 1)]
    return dates, dates[0], dates[-1]


def admin_required() -> None:
    if current_user.role != "teacher":
        abort(403)


def month_sum(stu_id: int, start: dt.date, end: dt.date) -> int:
    cnt = (
        Attendance.query.filter_by(student_id=stu_id)
        .filter(Attendance.date.between(start, end))
        .count()
    )
    return cnt * PRICE


@app.get("/")
def root() -> Response:
    return redirect(url_for("journal"))


@app.get("/journal")
@login_required
def journal():
    today = dt.date.today()
    y = int(request.args.get("y", today.year))
    m = int(request.args.get("m", today.month))
    days, d_start, d_end = month_info(y, m)

    studs = (
        Student.query.all()
        if current_user.role == "teacher"
        else Student.query.filter_by(parent_id=current_user.id).all()
    )

    attend: Dict[int, Set[str]] = {s.id: set() for s in studs}
    for a in Attendance.query.filter(
        Attendance.date.between(d_start, d_end)
    ).all():
        attend.setdefault(a.student_id, set()).add(a.date.isoformat())

    rows = [
        {
            "id": s.id,
            "name": s.name,
            "month_sum": month_sum(s.id, d_start, d_end),
        }
        for s in studs
    ]
    return render_template(
        "journal.html",
        year=y,
        month=m,
        days=days,
        students=rows,
        attend=attend,
        total=sum(r["month_sum"] for r in rows),
    )


@app.get("/students")
@login_required
def students():
    studs = (
        Student.query.all()
        if current_user.role == "teacher"
        else Student.query.filter_by(parent_id=current_user.id).all()
    )
    catalog = Song.query.all()
    mapping: Dict[int, List[Song]] = {
        s.id: [
            ps.song
            for ps in StudentSong.query.filter_by(student_id=s.id).all()
        ]
        for s in studs
    }
    return render_template(
        "students.html", students=studs, songs=catalog, mapping=mapping
    )


@app.get("/songs")
@login_required
def songs():
    return render_template("songs.html", songs=Song.query.all())


@app.post("/api/attendance/toggle")
@login_required
def toggle_attendance():
    admin_required()
    sid = request.json.get("student_id")
    d = dt.date.fromisoformat(request.json.get("date"))
    row = Attendance.query.filter_by(student_id=sid, date=d).first()
    if row:
        db.session.delete(row)
    else:
        db.session.add(Attendance(student_id=sid, date=d))
    db.session.commit()
    _, start, end = month_info(d.year, d.month)
    return jsonify(
        {
            "month_sum": month_sum(sid, start, end),
            "total": db.session.query(Attendance.id).count() * PRICE,
        }
    )


@app.post("/api/student")
@login_required
def add_student():
    admin_required()
    name = request.json.get("name", "").strip()
    if not name:
        abort(400)
    s = Student(name=name, parent_id=current_user.id)
    db.session.add(s)
    db.session.commit()
    return jsonify({"id": s.id, "name": s.name}), 201


@app.delete("/api/student/<int:sid>")
@login_required
def delete_student(sid: int):
    admin_required()
    db.session.execute(
        delete(StudentSong).where(StudentSong.student_id == sid)
    )
    db.session.execute(delete(Attendance).where(Attendance.student_id == sid))
    db.session.execute(delete(Student).where(Student.id == sid))
    db.session.commit()
    return "", 204


@app.post("/api/song")
@login_required
def add_song():
    admin_required()
    title = request.json.get("title", "").strip()
    author = request.json.get("author", "").strip()
    diff = int(request.json.get("difficulty", 1))
    if not title or not author:
        abort(400)
    song = Song(title=title, author=author, difficulty=diff)
    db.session.add(song)
    db.session.commit()
    return jsonify({"id": song.id}), 201


@app.delete("/api/song/<int:tid>")
@login_required
def delete_song(tid: int):
    admin_required()
    db.session.execute(delete(StudentSong).where(StudentSong.song_id == tid))
    db.session.execute(delete(Song).where(Song.id == tid))
    db.session.commit()
    return "", 204


@app.post("/api/assign")
@login_required
def assign():
    admin_required()
    sid = request.json.get("student_id")
    tid = request.json.get("song_id")
    if not (sid and tid):
        abort(400)
    db.session.merge(StudentSong(student_id=sid, song_id=tid))
    db.session.commit()
    return "", 201


@app.get("/healthz")
def health():
    return "ok", 200


def seed_initial_data() -> None:
    if User.query.first():
        return
    admin = User(
        email="teacher@example.com",
        password=generate_password_hash("secret"),
        role="teacher",
    )
    db.session.add(admin)
    db.session.flush()

    pupils = [
        "Діана",
        "Саша",
        "Андріана",
        "Маша",
        "Ліза",
        "Кіріл",
        "Остап",
        "Єва",
        "Валерія",
        "Аня",
        "Матвій",
        "Валентин",
        "Дем'ян",
        "Єгор",
        "Нікалай",
        "Глєб",
        "Георгій",
        "Данило",
    ]
    students = {n: Student(name=n, parent_id=admin.id) for n in pupils}
    db.session.add_all(students.values())

    songs_data = [
        ("deluciuos of savior", "Slaer", 1),
        ("Bluesуtone Aley", "Wei Congfei", 2),
        ("memories and dreams", "Sally Face", 1),
        ("come as you are", "Nirvana", 1),
        ("smells like teen spirit", "Nirvana", 1),
    ]
    songs = {
        t: Song(title=t, author=a, difficulty=d) for t, a, d in songs_data
    }
    db.session.add_all(songs.values())
    db.session.flush()

    link: Dict[str, List[str]] = {
        "Діана": [
            "Bluestone Alley",
            "deluciuos of savior",
            "smells like teen spirit",
            "memories and dreams",
        ],
        "Саша": ["memories and dreams", "come as you are"],
    }
    for pupil, songlist in link.items():
        sid = students[pupil].id
        for title in songlist:
            db.session.add(
                StudentSong(student_id=sid, song_id=songs[title].id)
            )
    db.session.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with app.app_context():
        db.create_all()
        seed_initial_data()
    app.run(host="0.0.0.0", port=5000, debug=True)
