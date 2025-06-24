1 from __future__ import annotations
 2 
 3 import pathlib, datetime as dt, calendar, logging
 4 from flask import Flask, render_template, jsonify, abort, request, redirect, url_for
 5 from flask_login import LoginManager, login_required, current_user
 6 from werkzeug.security import generate_password_hash
 7 from sqlalchemy import delete
 8 from models import db, User, Student, Song, Attendance, StudentSong
 9 
10 PRICE = 130
11 DATA_DIR = pathlib.Path("/data")
12 DATA_DIR.mkdir(parents=True, exist_ok=True)
13 
14 app = Flask(__name__, static_folder="static", template_folder="templates")
15 app.config.update(
16     SQLALCHEMY_DATABASE_URI=f"sqlite:///{DATA_DIR/'app.db'}",
17     SECRET_KEY="replace-me",
18     SQLALCHEMY_TRACK_MODIFICATIONS=False,
19 )
20 db.init_app(app)
21 
22 # ───── Вхід (Login) ─────
23 login = LoginManager(app)
24 login.login_view = "auth.login"
25 
26 @login.user_loader
27 def load_user(uid):
28     return db.session.get(User, uid)
29 
30 # ───── Ініціалізація блупрінта auth ─────
31 from auth import bp as auth_bp  # noqa: E402
32 app.register_blueprint(auth_bp)
33 
34 # ───── Допоміжні функції ─────
35 def month_info(year: int, month: int):
36     days_cnt = calendar.monthrange(year, month)[1]
37     dates = [dt.date(year, month, d) for d in range(1, days_cnt + 1)]
38     return dates, dates[0], dates[-1]
39 
40 def admin_required():
41     if current_user.role != "teacher":
42         abort(403, "Тільки адміністратор може виконати дію")
43 
44 def month_sum(stu_id: int, start: dt.date, end: dt.date) -> int:
45     cnt = Attendance.query.filter_by(student_id=stu_id)\
46         .filter(Attendance.date.between(start, end)).count()
47     return cnt * PRICE
48 
49 # ───── Маршрути (Routes) ─────
50 @app.get("/")
51 def root():
52     return redirect(url_for("journal"))
53 
54 # -------- журнал --------
55 @app.get("/journal")
56 @login_required
57 def journal():
58     today = dt.date.today()
59     y = int(request.args.get("y", today.year))
60     m = int(request.args.get("m", today.month))
61     days, d_start, d_end = month_info(y, m)
62     studs = (Student.query.all() if current_user.role == "teacher" else 
63              Student.query.filter_by(parent_id=current_user.id).all())
64     attend = {s.id: set() for s in studs}
65     for a in Attendance.query.filter(Attendance.date.between(d_start, d_end)).all():
66         attend.setdefault(a.student_id, set()).add(a.date.isoformat())
67     rows = [{"id": s.id, "name": s.name, "month_sum": month_sum(s.id, d_start, d_end)}
68             for s in studs]
69     return render_template("journal.html", year=y, month=m, days=days,
70                            students=rows, attend=attend,
71                            total=sum(r["month_sum"] for r in rows))
72 
73 # -------- учні --------
74 @app.get("/students")
75 @login_required
76 def students():
77     studs = (Student.query.all() if current_user.role == "teacher" 
78              else Student.query.filter_by(parent_id=current_user.id).all())
79     catalog = Song.query.all()
80     mapping = {s.id: [ps.song for ps in StudentSong.query.filter_by(student_id=s.id).all()]
81                for s in studs}
82     return render_template("students.html", students=studs, songs=catalog, mapping=mapping)
83 
84 # -------- пісні --------
85 @app.get("/songs")
86 @login_required
87 def songs():
88     return render_template("songs.html", songs=Song.query.all())
89 
90 # ───── API ─────
91 @app.post("/api/attendance/toggle")
92 @login_required
93 def toggle_attendance():
94     admin_required()
95     sid = request.json.get("student_id")
96     d = dt.date.fromisoformat(request.json.get("date"))
97     row = Attendance.query.filter_by(student_id=sid, date=d).first()
98     if row:
99         db.session.delete(row)
100    else:
101        db.session.add(Attendance(student_id=sid, date=d))
102    db.session.commit()
103    y, m = d.year, d.month
104    _, start, end = month_info(y, m)
105    m_sum = month_sum(sid, start, end)
106    total = db.session.query(Attendance.id).count() * PRICE
107    return jsonify({"month_sum": m_sum, "total": total})
108 
109 @app.post("/api/student")
110 @login_required
111 def add_student():
112     admin_required()
113     name = request.json.get("name", "").strip()
114     if not name:
115         abort(400)
116     s = Student(name=name, parent_id=current_user.id)
117     db.session.add(s)
118     db.session.commit()
119     return jsonify({"id": s.id, "name": s.name}), 201
120 
121 @app.delete("/api/student/<int:sid>")
122 @login_required
123 def delete_student(sid):
124     admin_required()
125     db.session.execute(delete(StudentSong).where(StudentSong.student_id == sid))
126     db.session.execute(delete(Attendance).where(Attendance.student_id == sid))
127     db.session.execute(delete(Student).where(Student.id == sid))
128     db.session.commit()
129     return "", 204
130 
131 @app.post("/api/song")
132 @login_required
133 def add_song():
134     admin_required()
135     title = request.json.get("title", "").strip()
136     author = request.json.get("author", "").strip()
137     diff = int(request.json.get("difficulty", 1))
138     if not title or not author:
139         abort(400)
140     song = Song(title=title, author=author, difficulty=diff)
141     db.session.add(song)
142     db.session.commit()
143     return jsonify({"id": song.id}), 201
144 
145 @app.delete("/api/song/<int:tid>")
146 @login_required
147 def delete_song(tid):
148     admin_required()
149     db.session.execute(delete(StudentSong).where(StudentSong.song_id == tid))
150     db.session.execute(delete(Song).where(Song.id == tid))
151     db.session.commit()
152     return "", 204
153 
154 @app.post("/api/assign")
155 @login_required
156 def assign():
157     admin_required()
158     sid = request.json.get("student_id")
159     tid = request.json.get("song_id")
160     if not (sid and tid):
161         abort(400)
162     db.session.merge(StudentSong(student_id=sid, song_id=tid))
163     db.session.commit()
164     return "", 201
165 
166 @app.get("/healthz")
167 def health():
168     return "ok", 200
169 
170 # ───── Початкові дані ─────
171 with app.app_context():
172     db.create_all()
173     if not User.query.first():
174         admin = User(email="teacher@example.com",
175                      password=generate_password_hash("secret"),
176                      role="teacher")
177         db.session.add(admin)
178         db.session.commit()
179     pupils = ["Діана", "Саша", "Андріана", "Маша", "Ліза", "Кіріл", "Остап",
180               "Єва", "Валерія", "Аня", "Матвій", "Валентин", "Дем'ян",
181               "Єгор", "Нікалай", "Глєб", "Георгій", "Данило"]
182     students = {n: Student(name=n, parent_id=admin.id) for n in pupils}
183     db.session.add_all(students.values())
184     songs_data = [
185         ("deluciuos of savior", "Slayer", 1),
186         ("Bluestone Alley", "Wei Congfei", 2),
187         ("memories and dreams", "Sally Face", 1),
188         ("come as you are", "Nirvana", 1),
189         ("smells like teen spirit", "Nirvana", 1),
190         ("Horimia", "Масару Ёкояма", 3),
191         ("falling down", "Lil Peep", 2),
192         ("sweet dreams", "Marilyn Manson", 1),
193         ("Chk chk boom", "Stray Kids", 3),
194         ("Щедрик", "Микола Леонтович", 2),
195         ("megalovania", "Undertale", 3),
196         ("feel good", "Gorillaz", 1),
197         ("Graze the roof", "Plants vs Zombies", 2),
198         ("смішні голоси", "Ногу Свело", 2),
199         ("маленький ковбой", "Олександр Вінницький", 3),
200         ("The Last of Us", "G. Santaolalla", 3),
201         ("носорігблюз", "Юрій Радзецький", 4),
202         ("enemy", "Imagine Dragons", 1),
203         ("Добрий вечір тобі", "Народна", 2),
204         ("червона калина", "Степан Чарнецький", 2),
205         ("snowdin town", "Undertale", 3),
206         ("7 nation army", "The White Stripes", 1),
207         ("Californication", "RHCP", 3),
208         ("polly", "Nirvana", 1),
209     ]
210     songs = {t: Song(title=t, author=a, difficulty=d) for t, a, d in songs_data}
211     db.session.add_all(songs.values())
212     db.session.commit()
213     link = {
214         "Діана": ["feel good", "deluciuos of savior", "Graze the roof", "Bluestone Alley", "smells like teen spirit"],
215         "Саша": ["deluciuos of savior", "memories and dreams", "come as you are", "smells like teen spirit"],
216         "Андріана": ["Bluestone Alley", "Horimia", "come as you are", "falling down"],
217         "Маша": ["sweet dreams", "smells like teen spirit", "memories and dreams", "Chk chk boom", "come as you are"],
218         "Ліза": ["sweet dreams", "Bluestone Alley", "Horimia", "Chk chk boom", "Щедрик"],
219         "Кіріл": ["sweet dreams", "megalovania", "deluciuos of savior", "feel good", "Graze the roof",
220                  "смішні голоси", "falling down", "маленький ковбой"],
221         "Остап": ["megalovania", "Добрий вечір тобі", "deluciuos of savior", "червона калина", "enemy",
222                   "snowdin town", "feel good", "come as you are", "sweet dreams", "sweet dreams"],
223         "Єва": ["Bluestone Alley", "deluciuos of savior", "falling down"],
224         "Валерія": ["sweet dreams", "smells like teen spirit"],
225         "Аня": ["falling down", "Californication", "The Last of Us", "Horimia", "deluciuos of savior",
226                 "memories and dreams", "sweet dreams", "come as you are", "polly"],
227         "Валентин": ["sweet dreams", "deluciuos of savior", "смішні голоси"],
228         "Дем'ян": ["sweet dreams"],
229         "Єгор": ["7 nation army", "come as you are", "Graze the roof", "memories and dreams", "megalovania", "falling down"],
230         "Нікалай": ["falling down", "смішні голоси"],
231         "Глєб": ["смішні голоси", "носорігблюз", "The Last of Us"],
232         "Георгій": ["маленький ковбой", "носорігблюз", "Bluestone Alley"],
233     }
234     for pupil, songlist in link.items():
235         sid = students[pupil].id
236         for title in songlist:
237             db.session.add(StudentSong(student_id=sid, song_id=songs[title].id))
238     db.session.commit()
239 
240 if __name__ == "__main__":
241     logging.basicConfig(level=logging.INFO)
242     app.run(host="0.0.0.0", port=5000, debug=True)
# app.py ───────────────────────────────────────────────────────────────
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Set

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    url_for,
    flash,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
    UserMixin,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────  WTForms (щоб шаблони працювали)  ──────────────────────
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):  # simple авторизація
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Увійти")

class RegisterForm(FlaskForm):  # реєстрація
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Пароль",
        validators=[DataRequired(), Length(min=6)],
    )
    role = SelectField(
        "Роль",
        choices=[("parent", "Батько/Мати"), ("teacher", "Вчитель")],
        default="parent",
    )
    submit = SubmitField("Зареєструватися")

# ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "data" / "app.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "CHANGE_ME_IN_PROD"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_FILE}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ────────────────────────────  MODELS  ────────────────────────────────
student_song = db.Table(
    "student_song",
    db.Column("student_id", db.Integer, db.ForeignKey("student.id")),
    db.Column("song_id", db.Integer, db.ForeignKey("song.id")),
    db.UniqueConstraint("student_id", "song_id", name="uix_student_song"),
)


class User(db.Model, UserMixin):  # type: ignore[misc]
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="parent")  # parent | teacher

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password, raw)


class Student(db.Model):  # type: ignore[misc]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    songs = db.relationship("Song", secondary=student_song, back_populates="students")


class Song(db.Model):  # type: ignore[misc]
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), unique=True, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    difficulty = db.Column(db.Integer, default=1)
    students = db.relationship("Student", secondary=student_song, back_populates="songs")


# ───────────────────────────  LOGIN  ──────────────────────────────────
@login_manager.user_loader
def load_user(user_id: str) -> User | None:  # noqa: D401
    return db.session.get(User, int(user_id))


# ───────────────────────────  ROUTES  ─────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("journal"))


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        pwd = form.password.data

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pwd):
            login_user(user)
            flash("Успішний вхід!", "success")
            return redirect(url_for("journal"))
        flash("Невірні дані", "danger")

    return render_template("login.html", form=form)


@app.route("/auth/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        pwd = form.password.data
        role = form.role.data

        if User.query.filter_by(email=email).first():
            flash("Такий email вже існує", "danger")
        else:
            user = User(
                email=email,
                password=generate_password_hash(pwd),
                role=role,
            )
            db.session.add(user)
            db.session.commit()
            flash("Успішна реєстрація, увійдіть!", "success")
            return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/journal")
@login_required
def journal():
    students: List[Student] = Student.query.order_by(Student.name).all()
    songs: List[Song] = Song.query.order_by(Song.title).all()
    return render_template("journal.html", students=students, songs=songs)


@app.route("/students")
@login_required
def students():
    studs = Student.query.order_by(Student.name).all()
    songs = Song.query.order_by(Song.title).all()
    return render_template("students.html", students=studs, songs=songs)


@app.route("/songs")
@login_required
def songs():
    songs = Song.query.order_by(Song.title).all()
    return render_template("songs.html", songs=songs)


# ───────────────────────────  SEED DATA  ──────────────────────────────
def seed_db() -> None:
    """Ідемпотентне первинне заповнення БД."""
    teacher_email = "teacher@example.com"
    if not User.query.filter_by(email=teacher_email).first():
        teacher = User(
            email=teacher_email,
            password=generate_password_hash("secret"),
            role="teacher",
        )
        db.session.add(teacher)

    SONG_CATALOGUE: List[Dict[str, str | int]] = [
        {"title": "deluciuos of savior", "author": "slayer", "difficulty": 1},
        {"title": "Bluestone Alley", "author": "WEI CONGFEI", "difficulty": 2},
        {"title": "memories and dreams", "author": "Sally Face", "difficulty": 1},
        {"title": "come as you are", "author": "nirvana", "difficulty": 1},
        {"title": "smells like teen spirit", "author": "nirvana", "difficulty": 1},
        # … за бажанням додайте решту
    ]
    for s in SONG_CATALOGUE:
        if not Song.query.filter_by(title=s["title"]).first():
            db.session.add(Song(**s))  # type: ignore[arg-type]

    db.session.commit()

    STUDENT_SONGS: Dict[str, List[str]] = {
        "Діана": [
            "Bluestone Alley",
            "Graze the roof",
            "deluciuos of savior",
            "smells like teen spirit",
            "gorillaz - feel good",
        ],
        "Саша": [
            "deluciuos of savior",
            "memories and dreams",
            "come as you are",
            "smells like teen spirit",
        ],
        # … решту списку
    }

    for pupil, titles in STUDENT_SONGS.items():
        student = Student.query.filter_by(name=pupil).first()
        if not student:
            student = Student(name=pupil)
            db.session.add(student)
            db.session.flush()
        existing_titles: Set[str] = {s.title for s in student.songs}
        for title in set(titles):
            if title in existing_titles:
                continue
            song = Song.query.filter_by(title=title).first()
            if song:
                student.songs.append(song)

    db.session.commit()


# ───────────────────────────  MAIN  ───────────────────────────────────
if __name__ == "__main__":
    if not DB_FILE.exists():
        DB_FILE.parent.mkdir(exist_ok=True)
    db.create_all()
    seed_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
