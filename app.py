
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "task_manager_secret_key_2026"

DATABASE = "task_manager.db"


# Database connection
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# Create database tables
def init_db():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


# Login protection
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.")
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


# Home
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not username or not email or not password:
            flash("All fields are required!")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        connection = get_db()

        try:
            connection.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )
            connection.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered!")

        finally:
            connection.close()

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db()
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        connection.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password!")

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    connection = get_db()

    tasks = connection.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        tasks=tasks,
        username=session["username"]
    )


# Add task
@app.route("/add_task", methods=["POST"])
@login_required
def add_task():
    title = request.form["title"].strip()
    description = request.form.get("description", "").strip()

    if not title:
        flash("Task title is required!")
        return redirect(url_for("dashboard"))

    connection = get_db()
    connection.execute(
        "INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
        (session["user_id"], title, description)
    )
    connection.commit()
    connection.close()

    flash("Task added successfully!")
    return redirect(url_for("dashboard"))


# Update task status
@app.route("/update_task/<int:task_id>", methods=["POST"])
@login_required
def update_task(task_id):
    status = request.form["status"]

    if status not in ["Pending", "Completed"]:
        flash("Invalid task status!")
        return redirect(url_for("dashboard"))

    connection = get_db()
    connection.execute(
        "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
        (status, task_id, session["user_id"])
    )
    connection.commit()
    connection.close()

    flash("Task status updated!")
    return redirect(url_for("dashboard"))


# Delete task
@app.route("/delete_task/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    connection = get_db()
    connection.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, session["user_id"])
    )
    connection.commit()
    connection.close()

    flash("Task deleted successfully!")
    return redirect(url_for("dashboard"))


# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully.")
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
