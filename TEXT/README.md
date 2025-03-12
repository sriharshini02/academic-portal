# Student Performance Analysis System

A comprehensive web-based application for analyzing and managing student academic performance through automated mark sheet processing and analysis.

## 🌟 Features

- **User Authentication**
  - Separate login portals for students and teachers
  - Secure registration and login system

- **Mark Sheet Processing**
  - Automated extraction of marks from uploaded images using OCR
  - Support for multiple image formats (PNG, JPG, JPEG, GIF)
  - Bulk upload capability for multiple mark sheets

- **Performance Analysis**
  - Detailed statistical analysis of student performance
  - Visual representations of marks distribution
  - Individual and class-wide performance tracking
  - Subject-wise analysis
  - Academic year-based tracking

- **Data Management**
  - Excel export functionality for mark sheets
  - Secure storage of student records
  - Easy access to historical performance data

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: MySQL
- **Image Processing**: OpenCV, Tesseract OCR
- **Data Analysis**: Pandas, NumPy
- **AI/ML**: Google Generative AI

## 📋 Prerequisites

- Python 3.x
- MySQL Server
- Tesseract OCR engine
- Virtual environment (recommended)

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Student-performance-analysis
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables in `.env` file:
   ```
   DB_HOST=your_host
   DB_USER=your_user
   DB_PASSWORD=your_password
   DB_NAME=your_database
   ```

5. Initialize the database:
   ```bash
   python database.py
   ```

## 🎯 Usage

1. Start the Flask application:
   ```bash
   python app.py
   ```

2. Access the application through your web browser at `http://localhost:5000`

3. Register as either a teacher or student

4. For teachers:
   - Upload mark sheets through the dashboard
   - View and analyze student performance
   - Generate reports and download data

5. For students:
   - View personal performance metrics
   - Track progress across subjects
   - Access historical performance data

## 📁 Project Structure

- `app.py`: Main application file with route definitions
- `database.py`: Database models and operations
- `image_to_text.py`: OCR functionality for mark sheet processing
- `text_to_json.py`: Text processing and JSON conversion
- `routes.py`: Additional route handlers
- `templates/`: HTML templates
- `static/`: Static files (CSS, JS, images)
- `uploads/`: Temporary storage for uploaded files

## 🔒 Security Features

- Password hashing for user authentication
- Session management
- Secure file upload handling
- Input validation and sanitization

