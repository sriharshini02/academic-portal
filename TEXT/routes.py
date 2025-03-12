from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from database.db_utils import UserAuth, CourseManager
from functools import wraps

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Replace with your secret key

auth = UserAuth()
course_manager = CourseManager()


# Login required decorator
def login_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session or session.get("role") != role:
                flash("Please login first.")
                return redirect(url_for(f"{role}_login"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@app.route("/")
def index():
    return render_template("portal.html")


@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        full_name = request.form["fullName"]
        student_id = request.form["studentId"]
        department = request.form["department"]
        password = request.form["password"]

        success, message = auth.register_student(
            full_name, student_id, department, password
        )
        if success:
            flash("Registration successful! Please login.")
            return redirect(url_for("student_login"))
        flash(message)
    return render_template("student_register.html")


@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():
    if request.method == "POST":
        full_name = request.form["fullName"]
        teacher_id = request.form["teacherId"]
        department = request.form["department"]
        specialization = request.form["specialization"]
        password = request.form["password"]

        success, message = auth.register_teacher(
            full_name, teacher_id, department, specialization, password
        )
        if success:
            flash("Registration successful! Please login.")
            return redirect(url_for("teacher_login"))
        flash(message)
    return render_template("teacher_register.html")


@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        student_id = request.form["studentId"]
        password = request.form["password"]

        student, message = auth.login_student(student_id, password)
        if student:
            session["user_id"] = student["id"]
            session["role"] = "student"
            session["name"] = student["full_name"]
            return redirect(url_for("student_dashboard"))
        flash(message)
    return render_template("student_login.html")


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        teacher_id = request.form["teacherId"]
        password = request.form["password"]

        teacher, message = auth.login_teacher(teacher_id, password)
        if teacher:
            session["user_id"] = teacher["id"]
            session["role"] = "teacher"
            session["name"] = teacher["full_name"]
            return redirect(url_for("teacher_dashboard"))
        flash(message)
    return render_template("teacher_login.html")


@app.route("/student/dashboard")
@login_required("student")
def student_dashboard():
    courses, message = course_manager.get_student_courses(session["user_id"])
    return render_template(
        "student_dashboard.html", name=session["name"], courses=courses or []
    )


@app.route("/teacher/dashboard")
@login_required("teacher")
def teacher_dashboard():
    courses, message = course_manager.get_teacher_courses(session["user_id"])
    return render_template(
        "teacher_dashboard.html", name=session["name"], courses=courses or []
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/student-analytics/<student_id>")
@login_required("student")
def get_student_analytics(student_id):
    try:
        # Get student's performance data
        results = course_manager.get_student_results(student_id)

        # Calculate analytics
        analytics = {
            "average_score": sum(r["total_marks"] for r in results) / len(results),
            "highest_score": max(r["total_marks"] for r in results),
            "lowest_score": min(r["total_marks"] for r in results),
            "performance_by_subject": {},
            "improvement_trend": [],
        }

        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/class-analytics/<class_id>")
@login_required("teacher")
def get_class_analytics(class_id):
    try:
        # Get class performance data
        results = course_manager.get_class_results(class_id)

        # Calculate class analytics
        analytics = {
            "class_average": 0,
            "top_performers": [],
            "subjects_analysis": {},
            "performance_distribution": {},
        }

        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
