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

            conn.commit()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
        finally:
            conn.close()


def check_existing_id(user_id):
    conn = create_connection()
    if conn:
        try:
            c = conn.cursor()

            # Check in students table
            c.execute("SELECT id FROM students WHERE id = ?", (user_id,))
            if c.fetchone():
                return True, "Student ID already exists"

            # Check in teachers table
            c.execute("SELECT id FROM teachers WHERE id = ?", (user_id,))
            if c.fetchone():
                return True, "Teacher ID already exists"

            return False, ""
        finally:
            conn.close()
    return True, "Database error"


def register_student(student_id, full_name, department, password):
    # Check if ID already exists
    exists, message = check_existing_id(student_id)
    if exists:
        return False, message

    conn = create_connection()
    if conn:
        try:
            c = conn.cursor()
            hashed_password = generate_password_hash(password)
            c.execute(
                "INSERT INTO students (id, full_name, department, password) VALUES (?, ?, ?, ?)",
                (student_id, full_name, department, hashed_password),
            )
            conn.commit()
            return True, "Student registration successful!"
        except sqlite3.Error as e:
            return False, f"Registration failed: {str(e)}"
        finally:
            conn.close()
    return False, "Database connection error"


def register_teacher(teacher_id, full_name, department, specialization, password):
    # Check if ID already exists
    exists, message = check_existing_id(teacher_id)
    if exists:
        return False, message

    conn = create_connection()
    if conn:
        try:
            c = conn.cursor()
            hashed_password = generate_password_hash(password)
            c.execute(
                "INSERT INTO teachers (id, full_name, department, specialization, password) VALUES (?, ?, ?, ?, ?)",
                (teacher_id, full_name, department, specialization, hashed_password),
            )
            conn.commit()
            return True, "Teacher registration successful!"
        except sqlite3.Error as e:
            return False, f"Registration failed: {str(e)}"
        finally:
            conn.close()
    return False, "Database connection error"


def verify_student(student_id, password):
    conn = create_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            student = c.fetchone()

            if not student:
                return False, "Invalid Student ID"

            if check_password_hash(student[3], password):
                return True, {
                    "id": student[0],
                    "full_name": student[1],
                    "department": student[2],
                }
            return False, "Invalid Password"
        finally:
            conn.close()
    return False, "Database connection error"


def verify_teacher(teacher_id, password):
    conn = create_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,))
            teacher = c.fetchone()

            if not teacher:
                return False, "Invalid Teacher ID"

            if check_password_hash(teacher[4], password):
                return True, {
                    "id": teacher[0],
                    "full_name": teacher[1],
                    "department": teacher[2],
                }
            return False, "Invalid Password"
        finally:
            conn.close()
    return False, "Database connection error"


class Database:
    def __init__(self, db_file="./database/exam_analysis.db"):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_file)

    def init_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create Teachers table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    department TEXT NOT NULL
                )
            """
            )

            # Create Classes table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year TEXT NOT NULL,  -- FY, SY, TY, Final
                    department TEXT NOT NULL,
                    academic_year TEXT NOT NULL
                )
            """
            )

            # Create Subjects table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    class_id INTEGER,
                    teacher_id INTEGER,
                    FOREIGN KEY (class_id) REFERENCES classes (id),
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                )
            """
            )

            # Create Exams table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_type TEXT NOT NULL,  -- MID1, MID2
                    subject_id INTEGER,
                    date_conducted DATE NOT NULL,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id)
                )
            """
            )

            # Create Student Results table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS student_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER,
                    roll_number TEXT NOT NULL,
                    Q1a INTEGER, Q1b INTEGER, Q1c INTEGER, Q1d INTEGER,
                    Q2a INTEGER, Q2b INTEGER, Q2c INTEGER, Q2d INTEGER,
                    Q3a INTEGER, Q3b INTEGER, Q3c INTEGER, Q3d INTEGER,
                    Q4a INTEGER, Q4b INTEGER, Q4c INTEGER, Q4d INTEGER,
                    Q5a INTEGER, Q5b INTEGER, Q5c INTEGER, Q5d INTEGER,
                    Q6a INTEGER, Q6b INTEGER, Q6c INTEGER, Q6d INTEGER,
                    total_marks INTEGER,
                    FOREIGN KEY (exam_id) REFERENCES exams (id)
                )
            """
            )

    def save_exam_results(self, exam_data, results_data):
        """Save exam results to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Insert exam details
            cursor.execute(
                """
                INSERT INTO exams (exam_type, subject_id, date_conducted)
                VALUES (?, ?, ?)
            """,
                (
                    exam_data["exam_type"],
                    exam_data["subject_id"],
                    datetime.now().date(),
                ),
            )

            exam_id = cursor.lastrowid

            # Insert student results
            for result in results_data:
                cursor.execute(
                    """
                    INSERT INTO student_results (
                        exam_id, roll_number,
                        Q1a, Q1b, Q1c, Q1d,
                        Q2a, Q2b, Q2c, Q2d,
                        Q3a, Q3b, Q3c, Q3d,
                        Q4a, Q4b, Q4c, Q4d,
                        Q5a, Q5b, Q5c, Q5d,
                        Q6a, Q6b, Q6c, Q6d,
                        total_marks
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        exam_id,
                        result["roll_number"],
                        *[
                            result["questions"][f"Q{i}"][part]
                            for i in range(1, 7)
                            for part in ["a", "b", "c", "d"]
                        ],
                        result["total_marks"],
                    ),
                )

    def get_analysis(self, class_id=None, exam_type=None, subject_id=None):
        """Get analysis of exam results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT 
                    COUNT(*) as total_students,
                    COUNT(CASE WHEN total_marks >= 40 THEN 1 END) as passed_students,
                    MAX(total_marks) as highest_mark,
                    MIN(total_marks) as lowest_mark,
                    AVG(total_marks) as average_mark
                FROM student_results sr
                JOIN exams e ON sr.exam_id = e.id
                JOIN subjects s ON e.subject_id = s.id
                WHERE 1=1
            """
            params = []

            if class_id:
                query += " AND s.class_id = ?"
                params.append(class_id)

            if exam_type:
                query += " AND e.exam_type = ?"
                params.append(exam_type)

            if subject_id:
                query += " AND s.id = ?"
                params.append(subject_id)

            cursor.execute(query, params)
            result = cursor.fetchone()

            if result:
                total_students, passed_students, highest, lowest, average = result
                pass_percentage = (
                    (passed_students / total_students * 100)
                    if total_students > 0
                    else 0
                )

                return {
                    "total_students": total_students,
                    "pass_percentage": round(pass_percentage, 2),
                    "highest_mark": highest,
                    "lowest_mark": lowest,
                    "average_mark": round(average, 2) if average else 0,
                }
            return None


class ResultsDatabase:
    def __init__(self, db_file="./database/exam_results.db"):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_file)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Drop existing tables if they exist
            cursor.execute("DROP TABLE IF EXISTS question_marks")
            cursor.execute("DROP TABLE IF EXISTS students_results")

            # Create tables for storing results
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS students_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    roll_number TEXT NOT NULL,
                    class_year TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    exam_type TEXT NOT NULL,
                    academic_year TEXT NOT NULL,
                    total_marks FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(roll_number, class_year, subject, exam_type, academic_year)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS question_marks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER NOT NULL,
                    question_number INTEGER NOT NULL,
                    part_a FLOAT DEFAULT 0,
                    part_b FLOAT DEFAULT 0,
                    part_c FLOAT DEFAULT 0,
                    part_d FLOAT DEFAULT 0,
                    FOREIGN KEY (result_id) REFERENCES students_results(id),
                    UNIQUE(result_id, question_number)
                )
            """
            )

    def save_results(self, results, class_year, subject, exam_type, academic_year):
        """Save results to database"""
        successful_saves = 0
        errors = []

        for entry in results:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    roll_number = entry.get("roll_number")
                    if not roll_number:
                        print("Missing roll number, skipping entry")
                        continue

                    # First check if this exact combination exists
                    cursor.execute(
                        """
                        SELECT id FROM students_results 
                        WHERE roll_number = ? AND class_year = ? AND subject = ? AND exam_type = ? AND academic_year = ?
                    """,
                        (roll_number, class_year, subject, exam_type, academic_year),
                    )

                    existing_record = cursor.fetchone()
                    total_marks = entry.get("total_marks", 0)
                    questions = entry.get("questions", {})

                    if existing_record:
                        # Update existing record
                        result_id = existing_record[0]
                        cursor.execute(
                            """
                            UPDATE students_results 
                            SET total_marks = ?
                            WHERE id = ?
                        """,
                            (total_marks, result_id),
                        )

                        # Delete existing question marks
                        cursor.execute(
                            "DELETE FROM question_marks WHERE result_id = ?",
                            (result_id,),
                        )
                    else:
                        # Insert new record
                        cursor.execute(
                            """
                            INSERT INTO students_results 
                            (roll_number, class_year, subject, exam_type, academic_year, total_marks)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                roll_number,
                                class_year,
                                subject,
                                exam_type,
                                academic_year,
                                total_marks,
                            ),
                        )
                        result_id = cursor.lastrowid

                    # Insert question marks
                    for q_num in range(1, 7):
                        q_key = f"Q{q_num}"
                        q_data = questions.get(q_key, {"a": 0, "b": 0, "c": 0, "d": 0})

                        cursor.execute(
                            """
                            INSERT INTO question_marks 
                            (result_id, question_number, part_a, part_b, part_c, part_d)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                result_id,
                                q_num,
                                q_data.get("a", 0),
                                q_data.get("b", 0),
                                q_data.get("c", 0),
                                q_data.get("d", 0),
                            ),
                        )

                    conn.commit()
                    successful_saves += 1
                    print(
                        f"Successfully processed result for roll number {roll_number}"
                    )

            except Exception as e:
                error_msg = f"Error processing result for {entry.get('roll_number', 'Unknown')}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                continue

        print(f"Total successful saves: {successful_saves}")
        if errors:
            print("Errors encountered:")
            for error in errors:
                print(error)

        return successful_saves

    def get_detailed_analysis(self, class_year, subject, exam_type):
        """Get detailed analysis of exam results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            analysis = {
                "overall_stats": {},
                "question_stats": {},
                "performance_trends": {},
                "student_distribution": {},
                "top_performers": [],
                "needs_improvement": [],
            }

            # Get overall statistics
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_students,
                    AVG(total_marks) as avg_marks,
                    MAX(total_marks) as max_marks,
                    MIN(total_marks) as min_marks,
                    COUNT(CASE WHEN total_marks >= 20 THEN 1 END) as passed_count
                FROM students_results
                WHERE class_year = ? AND subject = ? AND exam_type = ?
            """,
                (class_year, subject, exam_type),
            )

            result = cursor.fetchone()
            if result:
                total_students = result[0]
                analysis["overall_stats"] = {
                    "total_students": total_students,
                    "average_marks": round(result[1], 2) if result[1] else 0,
                    "highest_marks": result[2],
                    "lowest_marks": result[3],
                    "pass_percentage": (
                        round((result[4] / total_students * 100), 2)
                        if total_students > 0
                        else 0
                    ),
                }

            # Get question-wise statistics
            for q_num in range(1, 7):
                cursor.execute(
                    """
                    SELECT 
                        AVG(part_a) as avg_a,
                        AVG(part_b) as avg_b,
                        AVG(part_c) as avg_c,
                        AVG(part_d) as avg_d,
                        MAX(part_a + part_b + part_c + part_d) as max_total,
                        MIN(part_a + part_b + part_c + part_d) as min_total
                    FROM question_marks qm
                    JOIN students_results sr ON sr.id = qm.result_id
                    WHERE sr.class_year = ? AND sr.subject = ? 
                    AND sr.exam_type = ? AND qm.question_number = ?
                """,
                    (class_year, subject, exam_type, q_num),
                )

                q_stats = cursor.fetchone()
                if q_stats:
                    analysis["question_stats"][f"Q{q_num}"] = {
                        "average_marks": {
                            "a": round(q_stats[0], 2) if q_stats[0] else 0,
                            "b": round(q_stats[1], 2) if q_stats[1] else 0,
                            "c": round(q_stats[2], 2) if q_stats[2] else 0,
                            "d": round(q_stats[3], 2) if q_stats[3] else 0,
                        },
                        "max_total": q_stats[4],
                        "min_total": q_stats[5],
                    }

            # Get marks distribution
            cursor.execute(
                """
                SELECT 
                    CASE 
                        WHEN total_marks BETWEEN 0 AND 8 THEN '0-8'
                        WHEN total_marks BETWEEN 9 AND 16 THEN '9-16'
                        WHEN total_marks BETWEEN 17 AND 24 THEN '17-24'
                        WHEN total_marks BETWEEN 25 AND 32 THEN '25-32'
                        ELSE '33-40'
                    END as range,
                    COUNT(*) as count
                FROM students_results
                WHERE class_year = ? AND subject = ? AND exam_type = ?
                GROUP BY range
                ORDER BY range
            """,
                (class_year, subject, exam_type),
            )

            analysis["student_distribution"] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # Get top performers
            cursor.execute(
                """
                SELECT roll_number, total_marks
                FROM students_results
                WHERE class_year = ? AND subject = ? AND exam_type = ?
                ORDER BY total_marks DESC
                LIMIT 5
            """,
                (class_year, subject, exam_type),
            )

            analysis["top_performers"] = [
                {"roll_number": row[0], "marks": row[1]} for row in cursor.fetchall()
            ]

            # Get students needing improvement
            cursor.execute(
                """
                SELECT roll_number, total_marks
                FROM students_results
                WHERE class_year = ? AND subject = ? AND exam_type = ?
                    AND total_marks < (
                        SELECT AVG(total_marks) 
                        FROM students_results 
                        WHERE class_year = ? AND subject = ? AND exam_type = ?
                    )
                ORDER BY total_marks ASC
                LIMIT 5
            """,
                (class_year, subject, exam_type, class_year, subject, exam_type),
            )

            analysis["needs_improvement"] = [
                {"roll_number": row[0], "marks": row[1]} for row in cursor.fetchall()
            ]

            return analysis

    def update_result(self, roll_number, class_year, subject, exam_type, question_marks, total_marks):
        """Update marks for a student with improved error handling"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # First get the result ID
                cursor.execute(
                    """
                    SELECT id FROM students_results
                    WHERE roll_number = ? AND class_year = ? AND subject = ? AND exam_type = ?
                    """,
                    (roll_number, class_year, subject, exam_type)
                )
                
                result = cursor.fetchone()
                if not result:
                    print(f"Result not found for roll_number={roll_number}, class_year={class_year}, subject={subject}, exam_type={exam_type}")
                    return False, "Result not found"
                
                result_id = result[0]
                
                # Update the total marks
                cursor.execute(
                    """
                    UPDATE students_results
                    SET total_marks = ?
                    WHERE id = ?
                    """,
                    (total_marks, result_id)
                )
                
                # Update question marks
                for q_num, marks in question_marks.items():
                    # Extract question number from key (e.g., "Q1" -> 1)
                    q_number = int(q_num.replace("Q", ""))
                    
                    # Get part marks, defaulting to 0 if not provided
                    part_a = float(marks.get("a", 0))
                    part_b = float(marks.get("b", 0))
                    part_c = float(marks.get("c", 0))
                    part_d = float(marks.get("d", 0))
                    
                    # Check if question mark entry exists
                    cursor.execute(
                        """
                        SELECT id FROM question_marks
                        WHERE result_id = ? AND question_number = ?
                        """,
                        (result_id, q_number)
                    )
                    
                    if cursor.fetchone():
                        # Update existing question marks
                        cursor.execute(
                            """
                            UPDATE question_marks
                            SET part_a = ?, part_b = ?, part_c = ?, part_d = ?
                            WHERE result_id = ? AND question_number = ?
                            """,
                            (part_a, part_b, part_c, part_d, result_id, q_number)
                        )
                    else:
                        # Insert new question marks
                        cursor.execute(
                            """
                            INSERT INTO question_marks
                            (result_id, question_number, part_a, part_b, part_c, part_d)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (result_id, q_number, part_a, part_b, part_c, part_d)
                        )
                
                conn.commit()
                print(f"Successfully updated marks for roll_number={roll_number}")
                return True, "Marks updated successfully"
                
            except Exception as e:
                conn.rollback()
                print(f"Error updating marks: {str(e)}")
                return False, str(e)

    def delete_result(self, roll_number, class_year, subject, exam_type):
        """Delete a student's result"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # First get the result ID
                cursor.execute(
                    """
                    SELECT id FROM students_results
                    WHERE roll_number = ? AND class_year = ? AND subject = ? AND exam_type = ?
                """,
                    (roll_number, class_year, subject, exam_type),
                )

                result = cursor.fetchone()
                if not result:
                    return False, "Result not found"

                result_id = result[0]

                # Delete question marks first (due to foreign key constraint)
                cursor.execute(
                    "DELETE FROM question_marks WHERE result_id = ?", (result_id,)
                )

                # Then delete the main result
                cursor.execute(
                    """
                    DELETE FROM students_results
                    WHERE id = ?
                """,
                    (result_id,),
                )

                conn.commit()
                return True, "Result deleted successfully"
            except Exception as e:
                conn.rollback()
                return False, str(e)

    def get_student_results(self, roll_number):
        """Get all results for a specific student with improved handling for single exam case"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the roll number exists in the database
                cursor.execute(
                    "SELECT COUNT(*) FROM students_results WHERE roll_number = ?",
                    (roll_number,)
                )
                count = cursor.fetchone()[0]
                
                if count == 0:
                    print(f"No results found for roll number: {roll_number}")
                    return None
                
                # Get overall performance data
                cursor.execute(
                    """
                    SELECT 
                        subject,
                        exam_type,
                        class_year,
                        academic_year,
                        total_marks,
                        created_at
                    FROM students_results
                    WHERE roll_number = ?
                    ORDER BY created_at DESC
                    """,
                    (roll_number,)
                )
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "subject": row[0],
                        "exam_type": row[1],
                        "class_year": row[2],
                        "academic_year": row[3],
                        "total_marks": float(row[4]),  # Ensure it's a float
                        "date": row[5]
                    })
                
                # Get subject-wise performance with explicit casting to ensure proper numeric handling
                cursor.execute(
                    """
                    SELECT 
                        subject,
                        CAST(AVG(total_marks) AS REAL) as avg_marks,
                        CAST(MAX(total_marks) AS REAL) as max_marks,
                        COUNT(*) as exam_count
                    FROM students_results
                    WHERE roll_number = ?
                    GROUP BY subject
                    """,
                    (roll_number,)
                )
                
                subject_performance = []
                for row in cursor.fetchall():
                    subject = row[0]
                    avg_marks = round(float(row[1]), 2) if row[1] is not None else 0
                    max_marks = float(row[2]) if row[2] is not None else 0
                    exam_count = row[3]
                    
                    # If there's only one exam, get all marks for this subject to check if there are variations
                    if exam_count == 1:
                        cursor.execute(
                            """
                            SELECT total_marks
                            FROM students_results
                            WHERE roll_number = ? AND subject = ?
                            """,
                            (roll_number, subject)
                        )
                        subject_marks = [float(r[0]) for r in cursor.fetchall()]
                        
                        # If there are multiple entries with the same mark, add a note
                        if len(subject_marks) == 1:
                            note = "Only one exam taken"
                        else:
                            note = f"{len(subject_marks)} exams with same mark"
                    else:
                        note = f"{exam_count} exams taken"
                    
                    subject_performance.append({
                        "subject": subject,
                        "average_marks": avg_marks,
                        "highest_marks": max_marks,
                        "exam_count": exam_count,
                        "note": note
                    })
                
                # Get overall statistics with explicit casting
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_exams,
                        CAST(AVG(total_marks) AS REAL) as overall_avg,
                        CAST(MAX(total_marks) AS REAL) as highest_mark,
                        CAST(MIN(total_marks) AS REAL) as lowest_mark
                    FROM students_results
                    WHERE roll_number = ?
                    """,
                    (roll_number,)
                )
                
                stats_row = cursor.fetchone()
                
                # Process the stats with careful type handling
                if stats_row and stats_row[0] > 0:
                    total_exams = stats_row[0]
                    overall_average = round(float(stats_row[1]), 2) if stats_row[1] is not None else 0
                    highest_mark = float(stats_row[2]) if stats_row[2] is not None else 0
                    lowest_mark = float(stats_row[3]) if stats_row[3] is not None else 0
                    
                    # Check if this is a single exam case
                    single_exam_case = (total_exams == 1)
                    
                    overall_stats = {
                        "total_exams": total_exams,
                        "overall_average": overall_average,
                        "highest_mark": highest_mark,
                        "lowest_mark": lowest_mark,
                        "single_exam_case": single_exam_case
                    }
                else:
                    overall_stats = {
                        "total_exams": 0,
                        "overall_average": 0,
                        "highest_mark": 0,
                        "lowest_mark": 0,
                        "single_exam_case": False
                    }
                
                return {
                    "results": results,
                    "subject_performance": subject_performance,
                    "overall_stats": overall_stats
                }
        except Exception as e:
            print(f"Error in get_student_results: {e}")
            import traceback
            traceback.print_exc()
            return None

    def insert_test_marks(self, roll_number):
        """Insert test marks data for a student"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if test data already exists for this student
                cursor.execute(
                    "SELECT COUNT(*) FROM students_results WHERE roll_number = ?",
                    (roll_number,)
                )
                
                if cursor.fetchone()[0] > 0:
                    print(f"Test data already exists for student {roll_number}")
                    return True
                
                # Sample subjects and exam types
                subjects = ["Mathematics", "Physics", "Computer Science", "English", "Chemistry"]
                exam_types = ["Midterm", "Final", "Quiz", "Assignment"]
                current_year = "2023-2024"
                
                # Insert sample marks for each subject
                for subject in subjects:
                    for exam_type in exam_types[:2]:  # Just use Midterm and Final
                        # Generate a random mark between 60 and 95
                        total_marks = round(random.uniform(60, 95), 1)
                        
                        # Insert into students_results
                        cursor.execute(
                            """
                            INSERT INTO students_results 
                            (roll_number, class_year, subject, exam_type, academic_year, total_marks)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (roll_number, "Year 1", subject, exam_type, current_year, total_marks)
                        )
                        
                        # Get the result_id
                        result_id = cursor.lastrowid
                        
                        # Insert question marks
                        for q_num in range(1, 7):
                            part_a = round(random.uniform(3, 5), 1)
                            part_b = round(random.uniform(3, 5), 1)
                            part_c = round(random.uniform(3, 5), 1)
                            part_d = round(random.uniform(3, 5), 1)
                            
                            cursor.execute(
                                """
                                INSERT INTO question_marks 
                                (result_id, question_number, part_a, part_b, part_c, part_d)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (result_id, q_num, part_a, part_b, part_c, part_d)
                            )
                
                conn.commit()
                print(f"Successfully inserted test marks data for student {roll_number}")
                return True
                
        except Exception as e:
            print(f"Error inserting test data: {e}")
            return False


# Initialize the database when the module is imported
init_db()
