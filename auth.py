from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required, login_user, logout_user
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import EmailField, PasswordField, RadioField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError

from models import User, db

bp = Blueprint("auth", __name__, url_prefix="/auth")
ADMIN_INVITE_CODE = "admin123"


# ───── WTForms ─────
class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(6)])
    submit = SubmitField("Увійти")


class RegisterForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(6)])
    role = RadioField(
        "Роль",
        choices=[("parent", "Батьки / Учень"), ("teacher", "Адмін")],
        default="parent",
        validators=[DataRequired()],
    )
    admin_code = PasswordField("Код для адміна")
    submit = SubmitField("Зареєструватись")

    def validate_admin_code(form, field):
        if form.role.data == "teacher" and field.data != ADMIN_INVITE_CODE:
            raise ValidationError("Невірний admin‑код")


# ───── routes ─────
@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("journal"))
        flash("Невірний логін / пароль", "danger")
    return render_template("login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Email вже зареєстровано", "warning")
        else:
            user = User(
                email=form.email.data,
                password=generate_password_hash(form.password.data),
                role=form.role.data,
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)  # ← авто‑login
            return redirect(url_for("journal"))
    return render_template("register.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
