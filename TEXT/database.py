import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import random

if not os.path.exists("./database"):
    os.makedirs("./database")


def create_connection():
    try:
        conn = sqlite3.connect("./database/education.db")
        # Enable foreign key support (important for cascading deletes)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None


def init_db():
    conn = create_connection()
    if conn:
        try:
            c = conn.cursor()

            # Create students table
            c.execute(
                """CREATE TABLE IF NOT EXISTS students
                        (id TEXT PRIMARY KEY,
                         full_name TEXT NOT NULL,
                         department TEXT NOT NULL,
                         password TEXT NOT NULL)"""
            )

            # Create teachers table
            c.execute(
                """CREATE TABLE IF NOT EXISTS teachers
                        (id TEXT PRIMARY KEY,
                         full_name TEXT NOT NULL,
                         department TEXT NOT NULL,
                         specialization TEXT NOT NULL,
                         password TEXT NOT NULL)"""
            )

            # Create students_results table (exam results summary)
            c.execute(
                """CREATE TABLE IF NOT EXISTS students_results
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         roll_number TEXT NOT NULL,
                         class_year TEXT NOT NULL,
                         subject TEXT NOT NULL,
                         exam_type TEXT NOT NULL,
                         year INTEGER NOT NULL, -- Academic year (e.g., 2023)
                         total_marks REAL NOT NULL,
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"""
            )

            # Create question_marks table (detailed marks per question part)
            c.execute(
                """CREATE TABLE IF NOT EXISTS question_marks
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         result_id INTEGER NOT NULL,
                         question_number INTEGER NOT NULL,
                         part_a REAL NOT NULL,
                         part_b REAL NOT NULL,
                         part_c REAL NOT NULL,
                         part_d REAL NOT NULL,
                         FOREIGN KEY(result_id) REFERENCES students_results(id) ON DELETE CASCADE)"""
            )

            # --- New Tables for COs ---
            # Create courses table
            # Assuming a course is taught by one teacher and has a unique ID and name
            c.execute(
                """CREATE TABLE IF NOT EXISTS courses
                        (course_id TEXT PRIMARY KEY,
                         course_name TEXT NOT NULL,
                         teacher_id TEXT, -- Can be NULL initially if course created before teacher assignment
                         UNIQUE(course_id, teacher_id), -- A course can be taught by one teacher at a time
                         FOREIGN KEY(teacher_id) REFERENCES teachers(id) ON DELETE SET NULL)"""
            )

            conn.commit()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
        finally:
            conn.close()


def check_existing_id(user_id):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM students WHERE id = ? UNION SELECT id FROM teachers WHERE id = ?",
                (user_id, user_id),
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Error checking existing ID: {e}")
            return False
        finally:
            conn.close()


class Database:
    # No need for __init__ as methods create connections as needed
    # This prevents issues with long-lived connections and threading

    def register_student(self, full_name, student_id, department, password):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                if check_existing_id(student_id):
                    return False, "Student ID already exists."

                hashed_password = generate_password_hash(password)
                c.execute(
                    "INSERT INTO students (id, full_name, department, password) VALUES (?, ?, ?, ?)",
                    (student_id, full_name, department, hashed_password),
                )
                conn.commit()
                return True, "Student registered successfully."
            except sqlite3.Error as e:
                return False, f"Database error: {e}"
            finally:
                conn.close()

    def register_teacher(
        self, full_name, teacher_id, department, specialization, password
    ):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                if check_existing_id(teacher_id):
                    return False, "Teacher ID already exists."

                hashed_password = generate_password_hash(password)
                c.execute(
                    "INSERT INTO teachers (id, full_name, department, specialization, password) VALUES (?, ?, ?, ?, ?)",
                    (
                        teacher_id,
                        full_name,
                        department,
                        specialization,
                        hashed_password,
                    ),
                )
                conn.commit()
                return True, "Teacher registered successfully."
            except sqlite3.Error as e:
                return False, f"Database error: {e}"
            finally:
                conn.close()

    def verify_student(self, student_id, password):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT * FROM students WHERE id = ?", (student_id,))
                student = c.fetchone()
                if student and check_password_hash(
                    student[3], password
                ):  # student[3] is the hashed password
                    return {
                        "id": student[0],
                        "full_name": student[1],
                    }, "Login successful."
                return None, "Invalid student ID or password."
            except sqlite3.Error as e:
                return None, f"Database error: {e}"
            finally:
                conn.close()

    def verify_teacher(self, teacher_id, password):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,))
                teacher = c.fetchone()
                if teacher and check_password_hash(
                    teacher[4], password
                ):  # teacher[4] is the hashed password
                    return {
                        "id": teacher[0],
                        "full_name": teacher[1],
                        "department": teacher[2],
                        "specialization": teacher[3],
                    }, "Login successful."
                return None, f"Invalid teacher ID or password."
            except sqlite3.Error as e:
                return None, f"Database error: {e}"
            finally:
                conn.close()

    def get_teacher_info(self, teacher_id):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT full_name, department, specialization FROM teachers WHERE id = ?",
                    (teacher_id,),
                )
                return c.fetchone()
            except sqlite3.Error as e:
                print(f"Error getting teacher info: {e}")
                return None
            finally:
                conn.close()

    def get_student_info(self, student_id):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT full_name, department FROM students WHERE id = ?",
                    (student_id,),
                )
                return c.fetchone()
            except sqlite3.Error as e:
                print(f"Error getting student info: {e}")
                return None
            finally:
                conn.close()

    # --- Course management methods (needed for CO feature) ---
    def add_course(self, course_id, course_name, teacher_id):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    "INSERT OR IGNORE INTO courses (course_id, course_name, teacher_id) VALUES (?, ?, ?)",
                    (course_id, course_name, teacher_id),
                )
                conn.commit()
                return True, "Course added/updated successfully."
            except sqlite3.IntegrityError:
                return False, "Course ID already exists for this teacher."
            except sqlite3.Error as e:
                return False, f"Database error: {e}"
            finally:
                conn.close()

    def get_teacher_courses(self, teacher_id):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT course_id, course_name FROM courses WHERE teacher_id = ?",
                    (teacher_id,),
                )
                return [
                    {"course_id": row[0], "course_name": row[1]} for row in c.fetchall()
                ]
            except sqlite3.Error as e:
                print(f"Error getting teacher courses: {e}")
                return []
            finally:
                conn.close()


class ResultsDatabase:
    def insert_student_result(
        self, roll_number, class_year, subject, exam_type, year, total_marks
    ):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                # Check if result already exists for the same student, subject, exam_type, and academic_year
                c.execute(
                    """SELECT id FROM students_results
                    WHERE roll_number = ? AND subject = ? AND exam_type = ? AND year = ?""",
                    (roll_number, subject, exam_type, year),
                )
                existing_result = c.fetchone()

                if existing_result:
                    result_id = existing_result[0]
                    # Update total marks in students_results
                    c.execute(
                        """UPDATE students_results SET total_marks = ?, timestamp = CURRENT_TIMESTAMP
                        WHERE id = ?""",
                        (total_marks, result_id),
                    )
                    # Delete old question marks for this result_id
                    c.execute(
                        """DELETE FROM question_marks WHERE result_id = ?""",
                        (result_id,),
                    )
                    print(
                        f"Updated existing entry for {roll_number} - {subject} - {exam_type}"
                    )
                else:
                    # Insert new result into students_results
                    c.execute(
                        """INSERT INTO students_results
                        (roll_number, class_year, subject, exam_type, year, total_marks)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            roll_number,
                            class_year,
                            subject,
                            exam_type,
                            year,
                            total_marks,
                        ),
                    )
                    result_id = c.lastrowid
                    print(
                        f"Inserted new entry for {roll_number} - {subject} - {exam_type}"
                    )

                conn.commit()
                return result_id  # Return the result_id for inserting question marks
            except sqlite3.Error as e:
                print(f"Error inserting student result: {e}")
                return None
            finally:
                conn.close()

    def insert_question_marks(
        self, result_id, question_number, part_a, part_b, part_c, part_d
    ):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    """INSERT INTO question_marks
                    (result_id, question_number, part_a, part_b, part_c, part_d)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (result_id, question_number, part_a, part_b, part_c, part_d),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                print(f"Error inserting question marks: {e}")
                return False
            finally:
                conn.close()

    def get_all_results(self):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    """SELECT sr.id, sr.roll_number, sr.class_year, sr.subject, sr.exam_type, sr.year, sr.total_marks, sr.timestamp,
                                qm.question_number, qm.part_a, qm.part_b, qm.part_c, qm.part_d
                                FROM students_results sr
                                JOIN question_marks qm ON sr.id = qm.result_id
                                ORDER BY sr.timestamp DESC, sr.roll_number, qm.question_number"""
                )
                rows = c.fetchall()

                results = {}
                for row in rows:
                    (
                        result_id,
                        roll_number,
                        class_year,
                        subject,
                        exam_type,
                        year,
                        total_marks,
                        timestamp,
                        q_num,
                        part_a,
                        part_b,
                        part_c,
                        part_d,
                    ) = row
                    if result_id not in results:  # Group by result_id first
                        results[result_id] = {
                            "id": result_id,
                            "roll_number": roll_number,
                            "class_year": class_year,
                            "subject": subject,
                            "exam_type": exam_type,
                            "year": year,
                            "total_marks": total_marks,
                            "timestamp": timestamp,
                            "questions": {},
                        }
                    results[result_id]["questions"][f"Q{q_num}"] = {
                        "a": part_a,
                        "b": part_b,
                        "c": part_c,
                        "d": part_d,
                    }
                return list(results.values())
            except sqlite3.Error as e:
                print(f"Error fetching all results: {e}")
                return []
            finally:
                conn.close()

    def get_filtered_results(self, class_year, subject, exam_type):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    """SELECT sr.id, sr.roll_number, sr.class_year, sr.subject, sr.exam_type, sr.year, sr.total_marks, sr.timestamp,
                    qm.question_number, qm.part_a, qm.part_b, qm.part_c, qm.part_d
                    FROM students_results sr
                    JOIN question_marks qm ON sr.id = qm.result_id
                    WHERE sr.class_year = ? AND sr.subject = ? AND sr.exam_type = ?
                    ORDER BY sr.roll_number, qm.question_number""",
                    (class_year, subject, exam_type),
                )
                rows = c.fetchall()
                results = []
                current_result = None
                for row in rows:
                    (
                        result_id,
                        roll_number,
                        class_year_db,  # Use a different name to avoid conflict
                        subject_db,
                        exam_type_db,
                        year_db,
                        total_marks,
                        timestamp,
                        q_num,
                        part_a,
                        part_b,
                        part_c,
                        part_d,
                    ) = row
                    if not current_result or current_result["id"] != result_id:
                        if current_result:
                            results.append(current_result)
                        current_result = {
                            "id": result_id,
                            "roll_number": roll_number,
                            "class_year": class_year_db,
                            "subject": subject_db,
                            "exam_type": exam_type_db,  # Pass this exam_type to determine CO
                            "year": year_db,
                            "total_marks": total_marks,
                            "timestamp": timestamp,
                            "questions": {},
                        }
                    current_result["questions"][f"Q{q_num}"] = {
                        "a": part_a,
                        "b": part_b,
                        "c": part_c,
                        "d": part_d,
                    }
                if current_result:
                    results.append(current_result)
                return results
            except sqlite3.Error as e:
                print(f"Error getting filtered results: {e}")
                return []
            finally:
                conn.close()

    def delete_result(self, roll_number, class_year, subject, exam_type):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                # First, get the result_id to delete from question_marks
                c.execute(
                    "SELECT id FROM students_results WHERE roll_number = ? AND class_year = ? AND subject = ? AND exam_type = ?",
                    (roll_number, class_year, subject, exam_type),
                )
                result_row = c.fetchone()
                if result_row:
                    result_id = result_row[0]
                    # CASCADE DELETE should handle question_marks deletion, just delete from students_results
                    c.execute("DELETE FROM students_results WHERE id = ?", (result_id,))
                    conn.commit()
                    return True
                return False
            except sqlite3.Error as e:
                print(f"Error deleting result: {e}")
                return False
            finally:
                conn.close()

    def update_question_marks(self, result_id, question_data):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()

                for q_key, parts in question_data.items():
                    question_number_int = int(q_key.replace("Q", ""))
                    c.execute(
                        """UPDATE question_marks
                        SET part_a = ?, part_b = ?, part_c = ?, part_d = ?
                        WHERE result_id = ? AND question_number = ?""",
                        (
                            parts["a"],
                            parts["b"],
                            parts["c"],
                            parts["d"],
                            result_id,
                            question_number_int,
                        ),
                    )

                # Recalculate total_marks for students_results
                c.execute(
                    """SELECT SUM(part_a + part_b + part_c + part_d) FROM question_marks WHERE result_id = ?""",
                    (result_id,),
                )
                new_total_marks = c.fetchone()[0]
                c.execute(
                    """UPDATE students_results SET total_marks = ? WHERE id = ?""",
                    (new_total_marks, result_id),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                print(f"Error updating question marks: {e}")
                return False
            finally:
                conn.close()

    def get_unique_exam_details(self):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT DISTINCT class_year, subject, exam_type FROM students_results"
                )
                return c.fetchall()
            except sqlite3.Error as e:
                print(f"Error getting unique exam details: {e}")
                return []
            finally:
                conn.close()

    def get_student_results_for_dashboard(self, student_id):
        # This method is for basic summary, not used for detailed analytics anymore
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    """SELECT sr.total_marks, sr.subject, sr.exam_type, sr.year
                    FROM students_results sr
                    WHERE sr.roll_number = ?
                    ORDER BY sr.year, sr.subject, sr.exam_type""",
                    (student_id,),
                )
                rows = c.fetchall()
                # Convert to list of dictionaries for easier processing in app.py
                return [
                    {
                        "total_marks": r[0],
                        "subject": r[1],
                        "exam_type": r[2],
                        "year": r[3],
                    }
                    for r in rows
                ]
            except sqlite3.Error as e:
                print(f"Error getting student results for dashboard: {e}")
                return []
            finally:
                conn.close()

    def get_class_results_summary(self, class_year, subject, exam_type):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    """SELECT sr.roll_number, sr.total_marks
                    FROM students_results sr
                    WHERE sr.class_year = ? AND sr.subject = ? AND sr.exam_type = ?
                    ORDER BY sr.total_marks DESC""",
                    (class_year, subject, exam_type),
                )
                return [
                    {"roll_number": r[0], "total_marks": r[1]} for r in c.fetchall()
                ]
            except sqlite3.Error as e:
                print(f"Error getting class results summary: {e}")
                return {}
            finally:
                conn.close()

    def get_raw_question_marks_for_co_analysis(
        self, teacher_id, subject_name, exam_type=None, class_year=None
    ):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                # Select only results related to courses taught by this teacher
                # Assuming 'subject' column in students_results stores course_id/name

                # Start with base query to get all relevant question marks
                query = """
                    SELECT
                        sr.roll_number,
                        sr.exam_type,
                        qm.question_number,
                        qm.part_a, qm.part_b, qm.part_c, qm.part_d
                    FROM students_results sr
                    JOIN question_marks qm ON sr.id = qm.result_id
                    JOIN courses co ON sr.subject = co.course_id -- Join with courses to filter by teacher_id
                    WHERE co.teacher_id = ? AND sr.subject = ?
                """
                params = [teacher_id, subject_name]

                if exam_type:
                    query += " AND sr.exam_type = ?"
                    params.append(exam_type)
                if class_year:
                    query += " AND sr.class_year = ?"
                    params.append(class_year)

                query += " ORDER BY sr.roll_number, sr.exam_type, qm.question_number;"

                c.execute(query, params)
                return (
                    c.fetchall()
                )  # Returns list of tuples: (roll_number, exam_type, q_num, pa, pb, pc, pd)
            except sqlite3.Error as e:
                print(f"Error getting raw question marks for CO analysis: {e}")
                return []
            finally:
                conn.close()

    def insert_test_marks(self, roll_number):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                # Check if the student exists
                c.execute("SELECT id FROM students WHERE id = ?", (roll_number,))
                student_exists = c.fetchone()
                if not student_exists:
                    print(f"Student with roll number {roll_number} does not exist.")
                    return False

                # Ensure a default teacher exists for test courses if needed
                default_teacher_id = "TCH001"
                db_instance = (
                    Database()
                )  # Use Database class to register teacher/add course
                c.execute("SELECT id FROM teachers WHERE id = ?", (default_teacher_id,))
                if not c.fetchone():
                    db_instance.register_teacher(
                        "Test Teacher",
                        default_teacher_id,
                        "Computer Science",
                        "Programming",
                        "password123",
                    )

                subjects = [
                    "Math",
                    "Physics",
                    "Chemistry",
                ]  # These should correspond to actual course_ids/names
                exam_types = ["Mid 1", "Final"]  # Specific exam types for CO mapping
                current_year = datetime.now().year

                for subject in subjects:
                    # For test data, assume subject name acts as course_id for now
                    course_id_for_test = subject
                    # Ensure the course exists or add it (owned by default_teacher_id)
                    db_instance.add_course(
                        course_id_for_test, f"{subject} Course", default_teacher_id
                    )

                    for exam_type in exam_types:
                        # Prevent duplicate test data entries for the same student, subject, exam_type, year
                        c.execute(
                            """SELECT id FROM students_results
                            WHERE roll_number = ? AND subject = ? AND exam_type = ? AND year = ?""",
                            (roll_number, subject, exam_type, current_year),
                        )
                        if c.fetchone():
                            print(
                                f"Test data for {roll_number} - {subject} - {exam_type} ({current_year}) already exists. Skipping."
                            )
                            continue

                        total_marks = round(
                            random.uniform(50, 95), 1
                        )  # Example total marks

                        # Insert into students_results
                        c.execute(
                            """
                            INSERT INTO students_results
                            (roll_number, class_year, subject, exam_type, year, total_marks)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                roll_number,
                                "Year 1",
                                subject,
                                exam_type,
                                current_year,
                                total_marks,
                            ),
                        )

                        # Get the result_id
                        result_id = c.lastrowid

                        # Insert question marks
                        for q_num in range(1, 7):
                            part_a = round(random.uniform(3, 5), 1)
                            part_b = round(random.uniform(3, 5), 1)
                            part_c = round(random.uniform(3, 5), 1)
                            part_d = round(random.uniform(3, 5), 1)

                            c.execute(
                                """
                                INSERT INTO question_marks
                                (result_id, question_number, part_a, part_b, part_c, part_d)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (result_id, q_num, part_a, part_b, part_c, part_d),
                            )

                conn.commit()
                print(
                    f"Successfully inserted test marks data for student {roll_number}"
                )
                return True

            except Exception as e:
                print(f"Error inserting test data: {e}")
                return False

    # --- New method for student detailed results (including question marks) ---
    def get_student_detailed_results(self, roll_number):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT
                        sr.id, sr.roll_number, sr.class_year, sr.subject, sr.exam_type, sr.year, sr.total_marks, sr.timestamp,
                        qm.question_number, qm.part_a, qm.part_b, qm.part_c, qm.part_d
                    FROM students_results sr
                    JOIN question_marks qm ON sr.id = qm.result_id
                    WHERE sr.roll_number = ?
                    ORDER BY sr.year ASC, sr.timestamp ASC, sr.subject ASC, sr.exam_type ASC, qm.question_number ASC
                    """,
                    (roll_number,),
                )
                rows = c.fetchall()

                results = {}
                for row in rows:
                    (
                        result_id,
                        roll_number_db,
                        class_year,
                        subject,
                        exam_type,
                        year,
                        total_marks,
                        timestamp,
                        q_num,
                        part_a,
                        part_b,
                        part_c,
                        part_d,
                    ) = row
                    if result_id not in results:
                        results[result_id] = {
                            "id": result_id,
                            "roll_number": roll_number_db,
                            "class_year": class_year,
                            "subject": subject,
                            "exam_type": exam_type,
                            "year": year,
                            "total_marks": total_marks,
                            "timestamp": timestamp,
                            "questions": {},
                        }
                    results[result_id]["questions"][f"Q{q_num}"] = {
                        "a": part_a,
                        "b": part_b,
                        "c": part_c,
                        "d": part_d,
                    }
                return list(results.values())
            except sqlite3.Error as e:
                print(f"Error getting student detailed results: {e}")
                return []
            finally:
                conn.close()

    # --- Methods to get all distinct exam types and class years (for CO filter dropdowns) ---
    def get_all_exam_types(self):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT DISTINCT exam_type FROM students_results")
                return [row[0] for row in c.fetchall()]
            except sqlite3.Error as e:
                print(f"Error getting all exam types: {e}")
                return []
            finally:
                conn.close()

    def get_all_class_years(self):
        conn = create_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT DISTINCT class_year FROM students_results")
                return [row[0] for row in c.fetchall()]
            except sqlite3.Error as e:
                print(f"Error getting all class years: {e}")
                return []
            finally:
                conn.close()


# Initialize the database when the module is imported
init_db()
