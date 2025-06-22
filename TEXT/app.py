from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_file,
)
from database import (
    init_db,
    Database,  # Keep Database class for auth methods
    ResultsDatabase,
)
from functools import wraps
import os
from werkzeug.utils import secure_filename
from image_to_text import extract_text_from_image
from text_to_json import process_text_with_image
import pandas as pd
import json
from PIL import Image
from datetime import datetime
import re
import shutil
from zipfile import ZipFile
import tempfile
import openpyxl
import time
import threading
import sqlite3


app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Change this to a secure secret key

# Initialize the database
init_db()

db = Database()  # For user authentication and course management
db_results = ResultsDatabase()  # For student results and analysis


# Add these configurations
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)


# Helper function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --- New Helper Function for Course Outcomes ---
def get_course_outcome(exam_type, question_number):
    if exam_type == "Mid 1":
        if question_number in [1, 2]:
            return "CO1"
        elif question_number in [3, 4]:
            return "CO2"
        elif question_number in [5, 6]:
            return "CO3"
    elif exam_type == "Mid 2":
        if question_number in [1, 2]:
            return "CO3"
        elif question_number in [3, 4]:
            return "CO4"
        elif question_number in [5, 6]:
            return "CO5"
    # Default for unmapped questions or other exam types
    return "N/A"


# Login required decorator
def login_required(user_type):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session or session.get("user_type") != user_type:
                flash("Please log in to access this page.", "error")
                if user_type == "student":
                    return redirect(url_for("student_login"))
                elif user_type == "teacher":
                    return redirect(url_for("teacher_login"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@app.route("/")
def index():
    return render_template("portal.html")


@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        try:
            # Try to get JSON data first (for AJAX calls from JS)
            if request.is_json:
                data = request.get_json()
                student_id = data.get("studentId")
                full_name = data.get("fullName")
                department = data.get("department")
                password = data.get("password")
            else:  # Fallback to form data (for traditional form submits)
                student_id = request.form.get("studentId")
                full_name = request.form.get("fullName")
                department = request.form.get("department")
                password = request.form.get("password")

            if not all([student_id, full_name, department, password]):
                return (
                    jsonify({"success": False, "message": "All fields are required"}),
                    400,
                )

            success, message = db.register_student(
                full_name, student_id, department, password
            )
            if success:
                return jsonify({"success": True, "message": message}), 201
            else:
                return (
                    jsonify({"success": False, "message": message}),
                    409,
                )  # Conflict for existing ID
        except Exception as e:
            print(f"Error during student registration: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    return render_template("student_register.html")


@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():
    if request.method == "POST":
        try:
            if request.is_json:
                data = request.get_json()
                teacher_id = data.get("teacherId")
                full_name = data.get("fullName")
                department = data.get("department")
                specialization = data.get("specialization")
                password = data.get("password")
            else:
                teacher_id = request.form.get("teacherId")
                full_name = request.form.get("fullName")
                department = request.form.get("department")
                specialization = request.form.get("specialization")
                password = request.form.get("password")

            if not all([teacher_id, full_name, department, specialization, password]):
                return (
                    jsonify({"success": False, "message": "All fields are required"}),
                    400,
                )

            success, message = db.register_teacher(
                full_name, teacher_id, department, specialization, password
            )
            if success:
                return jsonify({"success": True, "message": message}), 201
            else:
                return jsonify({"success": False, "message": message}), 409
        except Exception as e:
            print(f"Error during teacher registration: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    return render_template("teacher_register.html")


@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        try:
            if request.is_json:
                data = request.get_json()
                student_id = data.get("studentId")
                password = data.get("password")
            else:
                student_id = request.form.get("studentId")
                password = request.form.get("password")

            if not all([student_id, password]):
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Both ID and password are required",
                        }
                    ),
                    400,
                )

            student, message = db.verify_student(student_id, password)
            if student:
                session["user_id"] = student["id"]
                session["user_type"] = "student"
                session["name"] = student["full_name"]
                # You might store other student info like department if needed in session
                return jsonify({"success": True, "message": message}), 200
            else:
                return jsonify({"success": False, "message": message}), 401
        except Exception as e:
            print(f"Error during student login: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    return render_template("student_login.html")


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        try:
            if request.is_json:
                data = request.get_json()
                teacher_id = data.get("teacherId")
                password = data.get("password")
            else:
                teacher_id = request.form.get("teacherId")
                password = request.form.get("password")

            if not all([teacher_id, password]):
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Both ID and password are required",
                        }
                    ),
                    400,
                )

            teacher_info, message = db.verify_teacher(teacher_id, password)
            if teacher_info:
                session["user_id"] = teacher_info["id"]
                session["user_type"] = "teacher"
                session["name"] = teacher_info["full_name"]
                session["department"] = teacher_info["department"]  # Store department
                session["specialization"] = teacher_info[
                    "specialization"
                ]  # Store specialization
                return jsonify({"success": True, "message": message}), 200
            else:
                return jsonify({"success": False, "message": message}), 401
        except Exception as e:
            print(f"Error during teacher login: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    return render_template("teacher_login.html")


@app.route("/student/dashboard")
@login_required("student")  # <-- Use the decorator with the role argument
def student_dashboard():
    student_id = session.get("user_id")
    student_name = session.get("name", "Student")
    department = session.get("department", "N/A")

    # Fetch student info from DB for full details, including department if not in session
    student_info_db = db.get_student_info(student_id)
    if student_info_db:
        student_name = student_info_db[0]
        department = student_info_db[1]

    return render_template(
        "student_dashboard.html",
        student_id=student_id,
        student_name=student_name,
        department=department,
    )


@app.route("/teacher/dashboard")
@login_required("teacher")
def teacher_dashboard():
    teacher_id = session.get("user_id")
    teacher_name = session.get("name", "Teacher")
    department = session.get("department", "N/A")
    specialization = session.get("specialization", "N/A")

    # Placeholder counts (implement database queries if you need dynamic counts)
    total_students = 0
    total_classes = 0
    total_subjects = 0
    recent_uploads = 0
    recent_activities = []

    return render_template(
        "teacher_dashboard.html",
        teacher_name=teacher_name,
        department=department,
        specialization=specialization,
        total_students=total_students,
        total_classes=total_classes,
        total_subjects=total_subjects,
        recent_uploads=recent_uploads,
        recent_activities=recent_activities,
    )


@app.route("/upload", methods=["GET", "POST"])
@login_required("teacher")
def upload_page():
    # Get courses taught by the current teacher
    teacher_id = session.get("user_id")
    teacher_courses = db.get_teacher_courses(teacher_id)

    # Define fixed class years and exam types
    class_years = [f"Year {i}" for i in range(1, 5)]
    exam_types = ["Mid 1", "Mid 2", "Final"]

    return render_template(
        "upload.html",
        teacher_courses=teacher_courses,
        class_years=class_years,
        exam_types=exam_types,
    )


@app.route("/process_upload", methods=["POST"])
@login_required("teacher")
def process_upload():
    any_file_uploaded = False
    if "folderUpload" in request.files:
        files = request.files.getlist("folderUpload")
        if files and files[0].filename != "":
            any_file_uploaded = True
    if not any_file_uploaded and "fileUpload" in request.files:
        files = request.files.getlist("fileUpload")
        if files and files[0].filename != "":
            any_file_uploaded = True

    if not any_file_uploaded:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No file selected for upload. Please choose a file or folder.",
                }
            ),
            400,
        )

    class_year = request.form.get("classYear")
    subject = request.form.get("subject")
    exam_type = request.form.get("examType")
    academic_year = datetime.now().year

    if not all([class_year, subject, exam_type]):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Missing form data (Class Year, Subject, or Exam Type).",
                }
            ),
            400,
        )

    uploaded_files = []
    if "folderUpload" in request.files:
        files = request.files.getlist("folderUpload")
        for file in files:
            if file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                uploaded_files.append(filepath)
            elif file.filename != "":
                print(
                    f"Skipping disallowed file type from folder upload: {file.filename}"
                )

    if "fileUpload" in request.files:
        files = request.files.getlist("fileUpload")
        for file in files:
            if file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                uploaded_files.append(filepath)
            elif file.filename != "":
                print(
                    f"Skipping disallowed file type from single file upload: {file.filename}"
                )

    if not uploaded_files:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No valid image files were found in your selection (only PNG, JPG, JPEG, GIF are allowed).",
                }
            ),
            400,
        )

    processed_count = 0
    for filepath in uploaded_files:
        try:
            extracted_data = extract_text_from_image(filepath)

            print(f"Extracted data from {filepath}: {extracted_data}")

            if extracted_data and isinstance(extracted_data, dict):
                roll_number = extracted_data.get("roll_number")
                questions_data = extracted_data.get("questions", {})
                total_marks = extracted_data.get("total_marks")

                if roll_number and total_marks is not None:
                    result_id = db_results.insert_student_result(
                        roll_number,
                        class_year,
                        subject,
                        exam_type,
                        academic_year,
                        total_marks,
                    )

                    if result_id:
                        for q_key, parts_data in questions_data.items():
                            question_number = int(q_key.replace("Q", ""))
                            db_results.insert_question_marks(
                                result_id,
                                question_number,
                                parts_data.get(
                                    "a", 0.0
                                ),  # Use 0.0 for float consistency
                                parts_data.get("b", 0.0),
                                parts_data.get("c", 0.0),
                                parts_data.get("d", 0.0),
                            )
                        processed_count += 1
            os.remove(filepath)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            pass

    if processed_count > 0:
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {processed_count} files",
                    "redirect": url_for("view_marks"),
                }
            ),
            200,
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Processing finished, but no valid data could be extracted from uploaded files.",
                }
            ),
            500,
        )


@app.route("/view_marks")
@login_required("teacher")
def view_marks():
    unique_details = db_results.get_unique_exam_details()
    class_years = sorted(list(set([d[0] for d in unique_details])))
    subjects = sorted(list(set([d[1] for d in unique_details])))
    exam_types = sorted(list(set([d[2] for d in unique_details])))

    return render_template(
        "view_marks.html",
        class_years=class_years,
        subjects=subjects,
        exam_types=exam_types,
    )


@app.route("/api/get_marks", methods=["GET"])
@login_required("teacher")
def get_marks():
    class_year = request.args.get("class_year")
    subject = request.args.get("subject")
    exam_type = request.args.get("exam_type")

    if not all([class_year, subject, exam_type]):
        return jsonify({"error": "Missing filter parameters"}), 400

    results = db_results.get_filtered_results(class_year, subject, exam_type)

    if results:
        for student_result in results:
            current_exam_type = student_result["exam_type"]
            for q_key, q_data in student_result["questions"].items():
                question_number = int(q_key.replace("Q", ""))
                q_data["co"] = get_course_outcome(current_exam_type, question_number)

        return jsonify({"success": True, "results": results}), 200
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No marks found for the selected filters.",
                }
            ),
            404,
        )


@app.route("/api/delete-marks", methods=["POST"])
@login_required("teacher")
def delete_marks():
    data = request.get_json()
    roll_number = data.get("roll_number")
    class_year = data.get("class_year")
    subject = data.get("subject")
    exam_type = data.get("exam_type")

    if not all([roll_number, class_year, subject, exam_type]):
        return jsonify({"success": False, "message": "Missing parameters"}), 400

    if db_results.delete_result(roll_number, class_year, subject, exam_type):
        return (
            jsonify({"success": True, "message": "Result deleted successfully!"}),
            200,
        )
    else:
        return jsonify({"success": False, "message": "Failed to delete result."}), 500


@app.route("/api/update-marks", methods=["POST"])
@login_required("teacher")
def update_marks():
    data = request.get_json()
    result_id = data.get("result_id")
    question_data = data.get("question_data")

    if not all([result_id, question_data]):
        return jsonify({"success": False, "message": "Missing parameters"}), 400

    if db_results.update_question_marks(result_id, question_data):
        return jsonify({"success": True, "message": "Marks updated successfully!"}), 200
    else:
        return jsonify({"success": False, "message": "Failed to update marks."}), 500


@app.route("/download_excel")
@login_required("teacher")
def download_excel():
    all_results = db_results.get_all_results()
    if not all_results:
        flash("No data available to download", "error")
        return redirect(url_for("view_marks"))

    question_part_columns = []
    if all_results:
        if all_results[0] and "questions" in all_results[0]:
            first_result_questions_keys = sorted(
                all_results[0]["questions"].keys(), key=lambda x: int(x[1:])
            )
            for q_num_str in first_result_questions_keys:
                question_part_columns.extend(
                    [f"{q_num_str}a", f"{q_num_str}b", f"{q_num_str}c", f"{q_num_str}d"]
                )

    columns = (
        [
            "Roll Number",
            "Class Year",
            "Subject",
            "Exam Type",
            "Academic Year",
        ]
        + question_part_columns
        + ["Total Marks"]
    )

    data_for_df = []
    for result in all_results:
        row = [
            result["roll_number"],
            result["class_year"],
            result["subject"],
            result["exam_type"],
            result["year"],
        ]

        for q_col in question_part_columns:
            q_num_str = q_col[:-1]
            part = q_col[-1]
            marks = result["questions"].get(q_num_str, {})
            row.append(marks.get(part, 0.0))

        row.append(result["total_marks"])
        data_for_df.append(row)

    df = pd.DataFrame(data_for_df, columns=columns)

    os.makedirs(TEMP_FOLDER, exist_ok=True)
    excel_file_path = os.path.join(TEMP_FOLDER, "results.xlsx")
    df.to_excel(excel_file_path, index=False)

    return send_file(excel_file_path, as_attachment=True, download_name="results.xlsx")


@app.route("/marks_analysis")
@login_required("teacher")
def marks_analysis():
    unique_details = db_results.get_unique_exam_details()
    class_years = sorted(list(set([d[0] for d in unique_details])))
    subjects = sorted(list(set([d[1] for d in unique_details])))
    exam_types = sorted(list(set([d[2] for d in unique_details])))

    return render_template(
        "marks_analysis.html",
        class_years=class_years,
        subjects=subjects,
        exam_types=exam_types,
    )


@app.route("/get_analysis", methods=["GET"])
@login_required("teacher")
def get_analysis():
    class_year = request.args.get("class_year")
    subject = request.args.get("subject")
    exam_type = request.args.get("exam_type")

    if not all([class_year, subject, exam_type]):
        return jsonify({"error": "Missing filter parameters"}), 400

    teacher_id = session.get("user_id")
    raw_marks_data = db_results.get_raw_question_marks_for_co_analysis(
        teacher_id, subject, exam_type, class_year
    )

    if not raw_marks_data:
        return (
            jsonify({"success": False, "message": "No data found for analysis."}),
            404,
        )

    total_scores = [sum(row[3:]) for row in raw_marks_data]
    average_overall = sum(total_scores) / len(total_scores) if total_scores else 0

    question_sums = {}
    question_counts = {}
    for _, _, q_num, pa, pb, pc, pd in raw_marks_data:
        if q_num not in question_sums:
            question_sums[q_num] = {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}
            question_counts[q_num] = 0
        question_sums[q_num]["a"] += pa
        question_sums[q_num]["b"] += pb
        question_sums[q_num]["c"] += pc
        question_sums[q_num]["d"] += pd
        question_counts[q_num] += 1

    question_analysis = []
    for q_num in sorted(question_sums.keys()):
        count = question_counts[q_num]
        if count > 0:
            question_analysis.append(
                {
                    "question": f"Q{q_num}",
                    "average_marks": {
                        "a": round(question_sums[q_num]["a"] / count, 2),
                        "b": round(question_sums[q_num]["b"] / count, 2),
                        "c": round(question_sums[q_num]["c"] / count, 2),
                        "d": round(question_sums[q_num]["d"] / count, 2),
                    },
                }
            )

    co_scores_sum = {}
    co_max_sum = {}
    max_marks_per_part = 5.0

    for roll_number, exam_type_db, q_num, pa, pb, pc, pd in raw_marks_data:
        co = get_course_outcome(exam_type_db, q_num)
        if co != "N/A":
            if co not in co_scores_sum:
                co_scores_sum[co] = 0.0
                co_max_sum[co] = 0.0

            co_scores_sum[co] += pa + pb + pc + pd
            co_max_sum[co] += 4 * max_marks_per_part

    co_performance = {}
    for co, total_obtained in co_scores_sum.items():
        total_max = co_max_sum[co]
        if total_max > 0:
            co_performance[co] = round((total_obtained / total_max) * 100, 2)
        else:
            co_performance[co] = 0

    analysis_data = {
        "average_overall": round(average_overall, 2),
        "question_analysis": question_analysis,
        "co_performance": co_performance,
        "top_performers": [],
        "needs_improvement": [],
    }

    return jsonify({"success": True, "data": analysis_data}), 200


@app.route("/teacher/add_course", methods=["GET", "POST"])
@login_required("teacher")
def add_course_page():
    if request.method == "POST":
        course_id = request.form.get("course_id")
        course_name = request.form.get("course_name")
        teacher_id = session.get("user_id")

        if not all([course_id, course_name, teacher_id]):
            flash("Missing course ID or name.", "error")
            return redirect(url_for("add_course_page"))

        success, message = db.add_course(course_id, course_name, teacher_id)
        if success:
            flash(message, "success")
        else:
            flash(message, "error")
        return redirect(url_for("add_course_page"))

    teacher_id = session.get("user_id")
    courses = db.get_teacher_courses(teacher_id)
    return render_template("add_course.html", courses=courses)


@app.route("/teacher/co-performance")
@login_required("teacher")
def teacher_co_performance_page():
    teacher_id = session.get("user_id")
    teacher_courses = db.get_teacher_courses(teacher_id)
    all_exam_types = db_results.get_all_exam_types()
    all_class_years = db_results.get_all_class_years()

    return render_template(
        "teacher_co_performance.html",
        teacher_courses=teacher_courses,
        exam_types=all_exam_types,
        class_years=all_class_years,
    )


@app.route("/api/teacher/co-performance-data", methods=["GET"])
@login_required("teacher")
def get_teacher_co_performance_data():
    teacher_id = session.get("user_id")
    course_id = request.args.get("course_id")
    exam_type = request.args.get("exam_type")
    class_year = request.args.get("class_year")

    if not all([course_id, exam_type, class_year]):
        return (
            jsonify(
                {"error": "Missing filter parameters (Course, Exam Type, Class Year)"}
            ),
            400,
        )

    raw_marks_data = db_results.get_raw_question_marks_for_co_analysis(
        teacher_id, course_id, exam_type, class_year
    )

    if not raw_marks_data:
        return (
            jsonify(
                {"success": False, "message": "No data found for the selected filters."}
            ),
            404,
        )

    student_co_attainment = {}
    max_marks_per_part = 5.0

    all_possible_cos = set()
    for q_num in range(1, 7):
        co = get_course_outcome(exam_type, q_num)
        if co != "N/A":
            all_possible_cos.add(co)
    sorted_possible_cos = sorted(list(all_possible_cos))

    for co in sorted_possible_cos:
        for roll_number, exam_type_db, q_num, pa, pb, pc, pd in raw_marks_data:
            if roll_number not in student_co_attainment:
                student_co_attainment[roll_number] = {
                    co: {"obtained": 0.0, "max": 0.0} for co in sorted_possible_cos
                }

            co_for_question = get_course_outcome(exam_type_db, q_num)
            if (
                co_for_question != "N/A"
                and co_for_question in student_co_attainment[roll_number]
            ):
                student_co_attainment[roll_number][co_for_question]["obtained"] += (
                    pa + pb + pc + pd
                )
                student_co_attainment[roll_number][co_for_question]["max"] += (
                    4 * max_marks_per_part
                )

    formatted_student_co_data = []
    for roll, co_data in student_co_attainment.items():
        student_row = {"roll_number": roll}
        for co, marks in co_data.items():
            attainment_percentage = (
                (marks["obtained"] / marks["max"]) * 100 if marks["max"] > 0 else 0
            )
            student_row[co] = round(attainment_percentage, 2)
        formatted_student_co_data.append(student_row)

    return (
        jsonify(
            {
                "success": True,
                "co_data": formatted_student_co_data,
                "co_labels": sorted_possible_cos,
            }
        ),
        200,
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("index"))


# --- API Endpoint for Student Analytics ---
@app.route("/api/student-analytics/<student_id>")
@login_required("student")
def get_student_analytics(student_id):
    try:
        student_detailed_results = db_results.get_student_detailed_results(student_id)

        if not student_detailed_results:
            return (
                jsonify(
                    {
                        "average_score": 0,
                        "highest_score": 0,
                        "lowest_score": 0,
                        "performance_by_subject": {},
                        "improvement_trend": [],
                        "co_performance": {},
                    }
                ),
                200,
            )

        total_scores_list = [r["total_marks"] for r in student_detailed_results]

        average_score = sum(total_scores_list) / len(total_scores_list)
        highest_score = max(total_scores_list)
        lowest_score = min(total_scores_list)

        subject_scores = {}
        subject_counts = {}
        for result in student_detailed_results:
            subject = result["subject"]
            if subject not in subject_scores:
                subject_scores[subject] = 0.0
                subject_counts[subject] = 0
            subject_scores[subject] += result["total_marks"]
            subject_counts[subject] += 1

        performance_by_subject = {
            subj: round(subject_scores[subj] / subject_counts[subj], 2)
            for subj in subject_scores
        }

        improvement_trend = []
        for result in student_detailed_results:
            label = f"{result['subject']} ({result['exam_type']} {result['year']})"
            improvement_trend.append({"label": label, "score": result["total_marks"]})

        student_co_attainment = {}
        max_marks_per_part = 5.0

        all_possible_student_cos = set()
        for result in student_detailed_results:
            exam_type_for_co = result["exam_type"]
            for q_num_str in result["questions"]:
                q_num = int(q_num_str.replace("Q", ""))
                co = get_course_outcome(exam_type_for_co, q_num)
                if co != "N/A":
                    all_possible_student_cos.add(co)
        sorted_student_cos = sorted(list(all_possible_student_cos))

        for co_label in sorted_student_cos:  # Initialize for all possible COs
            student_co_attainment[co_label] = {"obtained": 0.0, "max": 0.0}

        for result in student_detailed_results:
            exam_type_for_co = result["exam_type"]
            for q_key, parts_data in result["questions"].items():
                question_number = int(q_key.replace("Q", ""))
                co = get_course_outcome(exam_type_for_co, question_number)
                if co != "N/A" and co in student_co_attainment:
                    student_co_attainment[co]["obtained"] += sum(parts_data.values())
                    student_co_attainment[co]["max"] += 4 * max_marks_per_part

        co_performance_percentages = {}
        for co, marks_data in student_co_attainment.items():
            if marks_data["max"] > 0:
                co_performance_percentages[co] = round(
                    (marks_data["obtained"] / marks_data["max"]) * 100, 2
                )
            else:
                co_performance_percentages[co] = 0.0

        analytics = {
            "average_score": round(average_score, 1),
            "highest_score": round(highest_score, 1),
            "lowest_score": round(lowest_score, 1),
            "performance_by_subject": performance_by_subject,
            "improvement_trend": improvement_trend,
            "co_performance": co_performance_percentages,
        }

        return jsonify(analytics), 200
    except Exception as e:
        print(f"Error in student analytics: {e}")
        return jsonify({"error": str(e)}), 500
