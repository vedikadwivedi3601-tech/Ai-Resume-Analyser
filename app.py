from flask import Flask, request, render_template, redirect, session
from db import Base, engine, SessionLocal
from ai import analyze_resume
import models
import PyPDF2
import docx
import json
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "dev-only")

Base.metadata.create_all(bind=engine)


@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        db = SessionLocal()
        try:
            if db.query(models.User).filter_by(email=email).first():
                return "User already exists"
            db.add(models.User(email=email, password=password))
            db.commit()
        finally:
            db.close()
        return redirect("/login")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        db = SessionLocal()
        try:
            user = db.query(models.User).filter_by(email=email, password=password).first()
        finally:
            db.close()
        if user:
            session["user"] = user.email
            return redirect("/dashboard")
        return "Invalid credentials"
    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            error = "Passwords do not match"
        elif len(new_password) < 6:
            error = "Password must be at least 6 characters"
        else:
            db = SessionLocal()
            try:
                user = db.query(models.User).filter_by(email=email).first()
                if not user:
                    error = "No account found with this email"
                else:
                    user.password = new_password
                    db.commit()
                    return redirect("/login")
            finally:
                db.close()
    return render_template("forgot.html", error=error)
def history():
    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=session["user"]).first()
        reports = db.query(models.Reports).filter_by(user_id=user.id).all()
    finally:
        db.close()

    parsed = []
    for r in reports:
        try:
            res = json.loads(r.result)
        except Exception:
            res = {}
        parsed.append({"resume": r.resume_text or "", "result": res})

    return render_template("history.html", reports=parsed)

#Dahboard
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    result = None

    if request.method == "POST":
        user_goal = (request.form.get("role") or "").strip()
        resume_text = (request.form.get("resume") or "").strip()
        file = request.files.get("file")

        # read uploaded file (overrides pasted text)
        if file and file.filename != "":
            name = file.filename.lower()
            try:
                if name.endswith(".pdf"):
                    reader = PyPDF2.PdfReader(file)
                    resume_text = "".join(p.extract_text() or "" for p in reader.pages).strip()
                    if not resume_text:
                        result = {"error": "Could not read text from this PDF (it may be a scanned image)."}
                elif name.endswith(".docx"):
                    d = docx.Document(file)
                    resume_text = "\n".join(p.text for p in d.paragraphs).strip()
                else:
                    result = {"error": "Only .pdf and .docx files are supported."}
            except Exception as e:
                result = {"error": f"File error: {str(e)}"}

        # validate
        if not result:
            if not user_goal:
                result = {"error": "Please enter the role you want."}
            elif not resume_text:
                result = {"error": "Please paste your resume or upload a file."}

        # analyse
        if not result:
            resume_text = resume_text[:6000]
            result = analyze_resume(resume_text, user_goal)

            # save only successful analyses
            if not result.get("error"):
                db = SessionLocal()
                try:
                    user = db.query(models.User).filter_by(email=session["user"]).first()
                    db.add(models.Reports(
                        user_id=user.id,
                        resume_text=resume_text,
                        result=json.dumps(result),
                    ))
                    db.commit()
                except Exception as e:
                    db.rollback()
                    result = {"error": f"Database error: {str(e)}"}
                finally:
                    db.close()

    return render_template("dashboard.html", user=session["user"], result=result)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)