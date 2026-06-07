from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from storage import load_json, append_record


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

USERS_FILE = "users.json"


def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return route_function(*args, **kwargs)
    return wrapper


def admin_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("auth.login"))

        if session.get("role") != "admin":
            flash("Admin access only.", "error")
            return redirect(url_for("auth.account"))

        return route_function(*args, **kwargs)
    return wrapper


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
            return render_template("auth/register.html")

        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("auth/register.html")

        users = load_json(USERS_FILE)

        if any(user["email"].lower() == email for user in users):
            flash("An account with this email already exists.", "error")
            return render_template("auth/register.html")

        new_user = {
            "user_id": f"U{len(users) + 1:03}",
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "address": address,
            "phone": phone,
            "role": "customer"
        }

        append_record(USERS_FILE, new_user)
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        users = load_json(USERS_FILE)
        user = next((u for u in users if u["email"].lower() == email), None)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html")

        session["user_id"] = user["user_id"]
        session["name"] = user["name"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        flash("Logged in successfully.", "success")

        next_url = request.values.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/account")
@login_required
def account():
    users = load_json(USERS_FILE)
    user = next((u for u in users if u["user_id"] == session["user_id"]), None)

    if not user:
        session.clear()
        flash("Account not found. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    return render_template("auth/account.html", user=user)



# adminaccess testing purposes 
@auth_bp.route("/admin-test")
@admin_required
def admin_test():
    return "Admin Access Granted"

