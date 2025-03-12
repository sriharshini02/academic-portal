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
    register_student,
    register_teacher,
    verify_student,
    verify_teacher,
    Database,
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

db = Database()
db_results = ResultsDatabase()

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


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_type" not in session:
            flash("Please log in first", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    return render_template("portal.html")


@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        try:
            # Try to get JSON data first
            if request.is_json:
                data = request.get_json()
                student_id = data.get("studentId")
                full_name = data.get("fullName")
                department = data.get("department")
                password = data.get("password")
            else:
                # Fall back to form data
                student_id = request.form.get("studentId")
                full_name = request.form.get("fullName")
                department = request.form.get("department")
                password = request.form.get("password")

            if not all([student_id, full_name, department, password]):
                return (
                    jsonify({"success": False, "message": "All fields are required"}),
                    400,
                )

            success, message = register_student(
                student_id, full_name, department, password
            )

            if success:
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": "Registration successful! Please login.",
                        }
                    ),
                    200,
                )
            else:
                return jsonify({"success": False, "message": message}), 400

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    return render_template("student_register.html")


@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():
    if request.method == "POST":
        try:
            # Try to get JSON data first
            if request.is_json:
                data = request.get_json()
                teacher_id = data.get("teacherId")
                full_name = data.get("fullName")
                department = data.get("department")
                specialization = data.get("specialization")
                password = data.get("password")
            else:
                # Fall back to form data
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

            success, message = register_teacher(
                teacher_id, full_name, department, specialization, password
            )

            if success:
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": "Registration successful! Please login.",
                        }
                    ),
                    200,
                )
            else:
                return jsonify({"success": False, "message": message}), 400

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    return render_template("teacher_register.html")


@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        try:
            # Try to get JSON data first
            if request.is_json:
                data = request.get_json()
                student_id = data.get("studentId")
                password = data.get("password")
            else:
                # Fall back to form data
                student_id = request.form.get("studentId")
                password = request.form.get("password")

            if not student_id or not password:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Both ID and password are required",
                        }
                    ),
                    400,
                )

            success, result = verify_student(student_id, password)

            if success:
                session["user_id"] = student_id
                session["user_type"] = "student"
                session["full_name"] = result["full_name"]
                return jsonify({"success": True, "message": "Login successful"})
            else:
                return jsonify({"success": False, "message": result}), 401

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    return render_template("student_login.html")


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        try:
            # Try to get JSON data first
            if request.is_json:
                data = request.get_json()
                teacher_id = data.get("teacherId")
                password = data.get("password")
            else:
                # Fall back to form data
                teacher_id = request.form.get("teacherId")
                password = request.form.get("password")

            if not teacher_id or not password:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Both ID and password are required",
                        }
                    ),
                    400,
                )

            success, result = verify_teacher(teacher_id, password)

            if success:
                session["user_id"] = teacher_id
                session["user_type"] = "teacher"
                session["full_name"] = result["full_name"]
                return jsonify({"success": True, "message": "Login successful"})
            else:
                return jsonify({"success": False, "message": result}), 401

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    return render_template("teacher_login.html")


@app.route("/student/dashboard")
@login_required
def student_dashboard():
    if session.get("user_type") != "student":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))

    # Get student details from session
    student_id = session.get("user_id")
    
    # Debug print to check what's in the session
    print(f"Session data for student: {session}")
    
    # Connect to the database to get complete student information
    conn = sqlite3.connect("./database/education.db")
    cursor = conn.cursor()
    
    try:
        # Query the students table to get complete information
        cursor.execute(
            "SELECT id, full_name, department FROM students WHERE id = ?", 
            (student_id,)
        )
        student_data = cursor.fetchone()
        
        if student_data:
            # Create student info dictionary with database data
            student = {
                "roll_number": student_data[0],
                "name": student_data[1],
                "department": student_data[2],
                "class_year": session.get("class_year", "2023-2024")  # Default academic year if not in session
            }
            print(f"Found student in database: {student}")
        else:
            # Fallback to session data if database query fails
            student = {
                "roll_number": student_id,
                "name": session.get("full_name", "Student"),
                "department": session.get("department", "Computer Science"),  # Provide default values
                "class_year": session.get("class_year", "2023-2024")
            }
            print(f"Using session data for student: {student}")
    except Exception as e:
        print(f"Error retrieving student data: {e}")
        # Fallback with session data and defaults
        student = {
            "roll_number": student_id,
            "name": session.get("full_name", "Student"),
            "department": "Computer Science",  # Default department
            "class_year": "2023-2024"  # Default academic year
        }
    finally:
        conn.close()
    
    # Get student's marks and analysis from ResultsDatabase
    try:
        # Make sure we have a valid roll number
        if not student_id:
            flash("Student ID not found in session", "error")
            return redirect(url_for("index"))
            
        print(f"Fetching results for student ID: {student_id}")
        student_results = db_results.get_student_results(student_id)
        
        if student_results:
            print(f"Found results for student: {len(student_results.get('results', []))} records")
            
            # Ensure highest mark is properly set
            if student_results["overall_stats"]["highest_mark"] == 0 and student_results["results"]:
                # Calculate highest mark manually
                highest_mark = max(float(result["total_marks"]) for result in student_results["results"])
                student_results["overall_stats"]["highest_mark"] = highest_mark
                print(f"Manually set highest mark to: {highest_mark}")
        else:
            print("No results found for student")
            # Initialize with empty data
            student_results = {
                "results": [],
                "subject_performance": [],
                "overall_stats": {
                    "total_exams": 0,
                    "overall_average": 0,
                    "highest_mark": 0,
                    "lowest_mark": 0
                }
            }
    except Exception as e:
        print(f"Error retrieving student results: {e}")
        import traceback
        traceback.print_exc()
        # Initialize with empty data
        student_results = {
            "results": [],
            "subject_performance": [],
            "overall_stats": {
                "total_exams": 0,
                "overall_average": 0,
                "highest_mark": 0,
                "lowest_mark": 0
            }
        }
    
    # Print debug info
    print(f"Student data being sent to template: {student}")
    print(f"Overall stats: {student_results.get('overall_stats', {})}")
    if student_results.get('results'):
        print(f"First result: {student_results['results'][0]}")
    
    return render_template(
        "student_dashboard.html", 
        name=student["name"],
        student=student,
        results=student_results["results"],
        subject_performance=student_results["subject_performance"],
        overall_stats=student_results["overall_stats"]
    )


@app.route("/teacher/dashboard")
@login_required
def teacher_dashboard():
    if session.get("user_type") != "teacher":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))
    return render_template(
        "teacher_dashboard.html",
        teacher_name=session.get("full_name"),
        department=session.get("department"),
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("index"))


@app.route("/upload")
@login_required
def upload_page():
    if session.get("user_type") != "teacher":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))
    return render_template("upload.html")


@app.route("/api/analysis")
@login_required
def get_analysis():
    year = request.args.get("year")
    subject = request.args.get("subject")
    exam_type = request.args.get("examType")

    if not all([year, subject, exam_type]):
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        analysis = db_results.get_detailed_analysis(year, subject, exam_type)
        return jsonify(analysis)
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        return jsonify({"error": "Failed to fetch analysis"}), 500


def process_files(files):
    results = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                # Extract text from image
                extracted_result = extract_text_from_image(filepath)
                print(f"Extracted result: {extracted_result}")

                # Check if extraction was successful
                if not extracted_result or not isinstance(extracted_result, dict):
                    print(f"Invalid extraction result from {filename}")
                    continue

                # Get the extracted text from the result
                extracted_text = extracted_result.get("text")
                if not extracted_text:
                    print(f"No text content extracted from {filename}")
                    continue

                # Process the extracted text into structured data
                processed_data = process_text_with_image(extracted_text, filepath)

                if not processed_data:
                    print(f"Failed to process data from {filename}")
                    continue

                # Validate the processed data structure
                if not isinstance(processed_data, dict):
                    print(f"Invalid data format from {filename}")
                    continue

                # Ensure required fields exist
                required_fields = ["roll_number", "questions", "total_marks"]
                if not all(field in processed_data for field in required_fields):
                    print(f"Missing required fields in data from {filename}")
                    continue

                # Validate questions structure
                questions = processed_data.get("questions", {})
                if not isinstance(questions, dict):
                    print(f"Invalid questions format in {filename}")
                    continue

                # Validate question data structure
                valid_question = True
                for q_num in range(1, 7):
                    q_key = f"Q{q_num}"
                    if q_key not in questions:
                        questions[q_key] = {"a": 0, "b": 0, "c": 0, "d": 0}
                        continue

                    q_data = questions[q_key]
                    if not isinstance(q_data, dict) or not all(
                        part in q_data for part in ["a", "b", "c", "d"]
                    ):
                        print(f"Invalid format for question {q_key} in {filename}")
                        valid_question = False
                        break

                if not valid_question:
                    continue

                # Add to results if all validation passes
                results.append(processed_data)

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
            finally:
                # Clean up temporary file
                if os.path.exists(filepath):
                    os.remove(filepath)

    return results


@app.route("/upload-folder", methods=["POST"])
@login_required
def upload_folder():
    if session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "Unauthorized access"}), 403

    try:
        class_year = request.form.get("class")
        subject = request.form.get("subject")
        exam_type = request.form.get("examType")
        academic_year = str(datetime.now().year)

        if not all([class_year, subject, exam_type]):
            return (
                jsonify({"success": False, "message": "Missing required fields"}),
                400,
            )

        results = []
        files_to_process = []

        # Handle individual file uploads
        if "files[]" in request.files:
            files = request.files.getlist("files[]")
            if files and files[0].filename:
                files_to_process.extend([f for f in files if allowed_file(f.filename)])

        # Handle folder upload
        if "folder[]" in request.files:
            folder_files = request.files.getlist("folder[]")
            if folder_files and folder_files[0].filename:
                files_to_process.extend(
                    [f for f in folder_files if allowed_file(f.filename)]
                )

        if not files_to_process:
            return (
                jsonify({"success": False, "message": "No valid image files found"}),
                400,
            )

        # Process all collected files
        for file in files_to_process:
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                result = process_single_image(filepath)
                if result:
                    results.append(result)

                # Clean up the temporary file
                if os.path.exists(filepath):
                    os.remove(filepath)

            except Exception as e:
                print(f"Error processing {file.filename}: {str(e)}")
                continue

        if not results:
            return (
                jsonify({"success": False, "message": "No valid data extracted"}),
                400,
            )

        # Save to database
        db_results.save_results(results, class_year, subject, exam_type, academic_year)

        # Store in session for display
        session["upload_results"] = results

        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {len(results)} files",
                "redirect": url_for("show_results"),
            }
        )

    except Exception as e:
        print(f"Upload error: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Error processing files: {str(e)}"}),
            500,
        )


def process_single_image(file_path):
    """Process a single image file and return extracted data."""
    try:
        # Extract text from image
        extracted_result = extract_text_from_image(file_path)

        if not extracted_result or not isinstance(extracted_result, dict):
            print(f"Invalid extraction result from {file_path}")
            return None

        # Get the extracted text from the result
        extracted_text = extracted_result.get("text")
        if not extracted_text:
            print(f"No text content extracted from {file_path}")
            return None

        # Process the extracted text into structured data
        processed_data = process_text_with_image(extracted_text, file_path)

        if not processed_data:
            print(f"Failed to process data from {file_path}")
            return None

        return validate_processed_data(processed_data)

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return None


def validate_processed_data(data):
    """Validate processed data structure."""
    if not isinstance(data, dict):
        return None

    # Ensure required fields exist
    required_fields = ["roll_number", "questions", "total_marks"]
    if not all(field in data for field in required_fields):
        return None

    # Validate questions structure
    questions = data.get("questions", {})
    if not isinstance(questions, dict):
        return None

    # Validate question data structure
    for q_num in range(1, 7):
        q_key = f"Q{q_num}"
        if q_key not in questions:
            questions[q_key] = {"a": 0, "b": 0, "c": 0, "d": 0}
            continue

        q_data = questions[q_key]
        if not isinstance(q_data, dict) or not all(
            part in q_data for part in ["a", "b", "c", "d"]
        ):
            return None

        # Validate mark values
        for part in ["a", "b", "c", "d"]:
            mark = q_data[part]
            if not isinstance(mark, (int, float)) or not (0 <= mark <= 8):
                q_data[part] = 0

    return data


def extract_roll_number(text):
    """Extract roll number from text"""
    match = re.search(r"Roll No:?\s*([A-Z0-9]+)", text)
    return match.group(1) if match else "000000000000"


def extract_question_marks(text):
    """Extract question marks from text"""
    questions = {}
    for i in range(1, 7):
        questions[f"Q{i}"] = {"a": 0, "b": 0, "c": 0, "d": 0}

    # Extract marks using regex
    pattern = r"Q(\d+)[:\s]+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"
    matches = re.finditer(pattern, text)

    for match in matches:
        q_num = match.group(1)
        if 1 <= int(q_num) <= 6:
            questions[f"Q{q_num}"] = {
                "a": float(match.group(2)),
                "b": float(match.group(3)),
                "c": float(match.group(4)),
                "d": float(match.group(5)),
            }

    return questions


def calculate_total_marks(text):
    """Calculate total marks from text"""
    match = re.search(r"Total[:\s]+(\d+)", text)
    return float(match.group(1)) if match else 0


def get_or_create_subject(subject_name, class_name, academic_year):
    """Helper function to get or create subject ID"""
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get or create class
        cursor.execute(
            """
            SELECT id FROM classes 
            WHERE year = ? AND academic_year = ?
        """,
            (class_name, academic_year),
        )

        class_result = cursor.fetchone()
        if class_result:
            class_id = class_result[0]
        else:
            cursor.execute(
                """
                INSERT INTO classes (year, department, academic_year)
                VALUES (?, ?, ?)
            """,
                (class_name, "DEFAULT", academic_year),
            )
            class_id = cursor.lastrowid

        # Get or create subject
        cursor.execute(
            """
            SELECT id FROM subjects 
            WHERE name = ? AND class_id = ?
        """,
            (subject_name, class_id),
        )

        subject_result = cursor.fetchone()
        if subject_result:
            return subject_result[0]

        cursor.execute(
            """
            INSERT INTO subjects (name, class_id, teacher_id)
            VALUES (?, ?, ?)
        """,
            (subject_name, class_id, session.get("user_id")),
        )

        return cursor.lastrowid


@app.route("/results")
@login_required
def show_results():
    if session.get("user_type") != "teacher":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))

    # Get results from session
    json_data = session.get("upload_results", [])

    return render_template("results.html", json_data=json_data)


@app.route("/delete_last", methods=["POST"])
@login_required
def delete_last():
    if session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "Unauthorized access"}), 403

    json_data = session.get("upload_results", [])

    if not json_data:
        return jsonify({"success": False, "message": "No entries to delete"}), 400

    # Remove the last entry
    json_data.pop()
    session["upload_results"] = json_data

    return jsonify({"success": True, "message": "Last entry deleted successfully"})


@app.route("/download_excel")
@login_required
def download_excel():
    if session.get("user_type") != "teacher":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))

    json_data = session.get("upload_results", [])

    if not json_data:
        flash("No data available to download", "error")
        return redirect(url_for("show_results"))

    # Create a DataFrame from the JSON data
    rows = []
    for entry in json_data:
        row = {
            "Roll Number": entry.get("roll_number", ""),
        }

        # Add question marks
        for q_num in range(1, 7):
            q_key = f"Q{q_num}"
            if q_key in entry.get("questions", {}):
                q_data = entry["questions"][q_key]
                row[f"{q_key}a"] = q_data.get("a", 0)
                row[f"{q_key}b"] = q_data.get("b", 0)
                row[f"{q_key}c"] = q_data.get("c", 0)
                row[f"{q_key}d"] = q_data.get("d", 0)
            else:
                row[f"{q_key}a"] = 0
                row[f"{q_key}b"] = 0
                row[f"{q_key}c"] = 0
                row[f"{q_key}d"] = 0

        row["Total"] = entry.get("total_marks", 0)
        rows.append(row)

    df = pd.DataFrame(rows)

    # Create Excel file
    excel_file = os.path.join(app.config["UPLOAD_FOLDER"], "results.xlsx")
    df.to_excel(excel_file, index=False)

    # Return the file for download
    return send_file(excel_file, as_attachment=True)


@app.route("/marks-analysis")
@login_required
def marks_analysis():
    if session.get("user_type") != "teacher":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Get all classes from the classes table
        cursor.execute(
            """
            SELECT DISTINCT c.year, c.academic_year 
            FROM classes c
            ORDER BY c.academic_year DESC, c.year
        """
        )
        class_years = [f"{row[0]} ({row[1]})" for row in cursor.fetchall()]

        # Get all subjects from the subjects table
        cursor.execute(
            """
            SELECT DISTINCT s.name 
            FROM subjects s
            JOIN classes c ON s.class_id = c.id
            ORDER BY s.name
        """
        )
        all_subjects = [row[0] for row in cursor.fetchall()]

    with db_results.get_connection() as conn:
        cursor = conn.cursor()

        # Get all unique class years from results
        cursor.execute(
            """
            SELECT DISTINCT class_year 
            FROM students_results 
            ORDER BY class_year
        """
        )
        result_years = [row[0] for row in cursor.fetchall()]

        # Get all unique subjects from results
        cursor.execute(
            """
            SELECT DISTINCT subject 
            FROM students_results 
            ORDER BY subject
        """
        )
        result_subjects = [row[0] for row in cursor.fetchall()]

        # Get all unique exam types
        cursor.execute(
            """
            SELECT DISTINCT exam_type 
            FROM students_results 
            ORDER BY exam_type
        """
        )
        exam_types = [row[0] for row in cursor.fetchall()]

        # Get summary statistics for each class and subject
        cursor.execute(
            """
            SELECT 
                class_year,
                subject,
                exam_type,
                COUNT(*) as total_students,
                AVG(total_marks) as avg_marks,
                MAX(total_marks) as max_marks,
                MIN(total_marks) as min_marks,
                COUNT(CASE WHEN total_marks >= 20 THEN 1 END) as passed_count
            FROM students_results
            GROUP BY class_year, subject, exam_type
            ORDER BY class_year, subject, exam_type
        """
        )

        class_stats = {}
        for row in cursor.fetchall():
            if row[0] not in class_stats:
                class_stats[row[0]] = {}
            if row[1] not in class_stats[row[0]]:
                class_stats[row[0]][row[1]] = {}

            total_students = row[3]
            class_stats[row[0]][row[1]][row[2]] = {
                "total_students": total_students,
                "avg_marks": round(row[4], 2) if row[4] else 0,
                "max_marks": row[5],
                "min_marks": row[6],
                "pass_percentage": (
                    round((row[7] / total_students * 100), 2)
                    if total_students > 0
                    else 0
                ),
            }

    # Combine years and subjects from both databases
    years = sorted(set(class_years + result_years))
    subjects = sorted(set(all_subjects + result_subjects))

    return render_template(
        "marks_analysis.html",
        teacher_name=session.get("full_name"),
        years=years,
        subjects=subjects,
        exam_types=exam_types,
        class_stats=class_stats,
    )


@app.route("/view_marks")
@login_required
def view_marks():
    if session.get("user_type") != "teacher":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))
    
    # Get available class years and exam types
    try:
        conn = sqlite3.connect("./database/exam_results.db")
        cursor = conn.cursor()
        
        # Get distinct class years
        cursor.execute("SELECT DISTINCT class_year FROM students_results")
        years = [row[0] for row in cursor.fetchall()]
        
        # Get distinct exam types
        cursor.execute("SELECT DISTINCT exam_type FROM students_results")
        exam_types = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template(
            "view_marks.html",
            years=years,
            exam_types=exam_types
        )
        
    except Exception as e:
        print(f"Error loading view marks page: {str(e)}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("teacher_dashboard"))


@app.route("/api/view-marks")
@login_required
def api_view_marks():
    if session.get("user_type") != "teacher":
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Get query parameters
    class_year = request.args.get("year")
    subject = request.args.get("subject")
    exam_type = request.args.get("examType")
    
    if not all([class_year, subject, exam_type]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        # Connect to the database
        conn = sqlite3.connect("./database/exam_results.db")
        cursor = conn.cursor()
        
        # Get all results matching the criteria
        cursor.execute(
            """
            SELECT sr.id, sr.roll_number, sr.subject, sr.total_marks
            FROM students_results sr
            WHERE sr.class_year = ? AND sr.subject = ? AND sr.exam_type = ?
            ORDER BY sr.roll_number
            """,
            (class_year, subject, exam_type)
        )
        
        results = []
        for row in cursor.fetchall():
            result_id, roll_number, subject_name, total_marks = row
            
            # Get question marks for this result
            cursor.execute(
                """
                SELECT question_number, part_a, part_b, part_c, part_d
                FROM question_marks
                WHERE result_id = ?
                ORDER BY question_number
                """,
                (result_id,)
            )
            
            questions = {}
            for q_row in cursor.fetchall():
                q_num, part_a, part_b, part_c, part_d = q_row
                questions[f"Q{q_num}"] = {
                    "a": part_a,
                    "b": part_b,
                    "c": part_c,
                    "d": part_d
                }
            
            # Fill in missing questions with zeros
            for i in range(1, 7):
                if f"Q{i}" not in questions:
                    questions[f"Q{i}"] = {"a": 0, "b": 0, "c": 0, "d": 0}
            
            results.append({
                "roll_number": roll_number,
                "subject": subject_name,
                "total_marks": total_marks,
                "questions": questions
            })
        
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        print(f"Error fetching marks: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/update-marks", methods=["POST"])
@login_required
def api_update_marks():
    if session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "Unauthorized access"}), 403
    
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ["roll_number", "class_year", "subject", "exam_type", "questions", "total_marks"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Update the marks in the database
        success, message = db_results.update_result(
            data["roll_number"],
            data["class_year"],
            data["subject"],
            data["exam_type"],
            data["questions"],
            data["total_marks"]
        )
        
        return jsonify({"success": success, "message": message})
        
    except Exception as e:
        print(f"Error updating marks: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/delete-marks", methods=["POST"])
@login_required
def api_delete_marks():
    if session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "Unauthorized access"}), 403
    
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ["roll_number", "class_year", "subject", "exam_type"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Delete the result from the database
        success, message = db_results.delete_result(
            data["roll_number"],
            data["class_year"],
            data["subject"],
            data["exam_type"]
        )
        
        return jsonify({"success": success, "message": message})
        
    except Exception as e:
        print(f"Error deleting marks: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/download-marks")
@login_required
def api_download_marks():
    if session.get("user_type") != "teacher":
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Get query parameters
    class_year = request.args.get("year")
    subject = request.args.get("subject")
    exam_type = request.args.get("examType")
    
    if not all([class_year, subject, exam_type]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        # Get marks data
        response = api_view_marks()
        if isinstance(response, tuple):
            return response
        
        marks_data = response.json
        
        # Create Excel file
        import pandas as pd
        from io import BytesIO
        
        # Prepare data for Excel
        excel_data = []
        for entry in marks_data:
            row = {
                "Roll Number": entry["roll_number"],
                "Subject": entry["subject"],
                "Total Marks": entry["total_marks"]
            }
            
            # Add question marks
            for q_num in range(1, 7):
                q_key = f"Q{q_num}"
                if q_key in entry["questions"]:
                    q_data = entry["questions"][q_key]
                    row[f"{q_key}_a"] = q_data["a"]
                    row[f"{q_key}_b"] = q_data["b"]
                    row[f"{q_key}_c"] = q_data["c"]
                    row[f"{q_key}_d"] = q_data["d"]
                else:
                    row[f"{q_key}_a"] = 0
                    row[f"{q_key}_b"] = 0
                    row[f"{q_key}_c"] = 0
                    row[f"{q_key}_d"] = 0
            
            excel_data.append(row)
        
        # Create DataFrame and Excel file
        df = pd.DataFrame(excel_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Marks')
        
        output.seek(0)
        
        # Generate filename
        filename = f"{subject}_{exam_type}_{class_year}_marks.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"Error generating Excel: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/insert_test_data_for_student/<roll_number>")
@login_required
def insert_test_data_for_student(roll_number):
    if session.get("user_type") != "teacher":
        flash("Unauthorized access", "error")
        return redirect(url_for("index"))
    
    try:
        # Insert test data for the student
        success = db_results.insert_test_marks(roll_number)
        
        if success:
            flash(f"Test data inserted successfully for student {roll_number}", "success")
        else:
            flash(f"Failed to insert test data for student {roll_number}", "error")
        
        return redirect(url_for("teacher_dashboard"))
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("teacher_dashboard"))


@app.route("/api/student_data/<roll_number>")
@login_required
def api_student_data(roll_number):
    if session.get("user_type") != "teacher":
        return jsonify({"error": "Unauthorized access"}), 403
    
    try:
        # Get student's marks and analysis
        student_results = db_results.get_student_results(roll_number)
        
        if not student_results:
            return jsonify({"error": "No data found for student"}), 404
        
        # Return the raw data
        return jsonify(student_results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
