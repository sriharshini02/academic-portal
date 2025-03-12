import cv2
import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.getenv("API_KEY")
genai.configure(api_key=API_KEY)


def extract_text_from_image(image_path):
    """Extract text from image using Gemini API."""
    try:
        # Load the image
        image_part = Image.open(image_path)

        # Configure Gemini
        generation_config = {
            "temperature": 0.1,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048,
        }

        # Initialize model
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash", generation_config=generation_config
        )

        # Create focused prompt for mark extraction
        prompt = """
        Analyze this answer sheet image and extract ONLY the following information in JSON format:
        
        1. Roll Number (exactly as shown, including 'A' prefix)
        2. For each question (Q1-Q6):
           - Extract marks for parts a, b, c, d
           - If a part has no marks, use 0
           - Marks should be numbers, not strings
        3. Total marks as shown on the sheet
        
        Important rules:
        - Look for marks in the "Marks Awarded" row
        - Some questions might have a total below them (e.g., "10" under Q2)
        - Only extract marks that are clearly visible
        - Return the data in this exact JSON structure:
        
        {
            "roll_number": "A...",
            "questions": {
                "Q1": {"a": 0, "b": 0, "c": 0, "d": 0},
                "Q2": {"a": 0, "b": 0, "c": 0, "d": 0},
                "Q3": {"a": 0, "b": 0, "c": 0, "d": 0},
                "Q4": {"a": 0, "b": 0, "c": 0, "d": 0},
                "Q5": {"a": 0, "b": 0, "c": 0, "d": 0},
                "Q6": {"a": 0, "b": 0, "c": 0, "d": 0}
            },
            "total_marks": 23
        }

        For the image shown:
        - Roll Number is A23126551134
        - Q2 has marks: a=5, b=5 (total 10)
        - Q4 has marks: a=5, b=8 (total 13)
        - Total marks = 23
        """

        # Generate response
        response = model.generate_content([image_part, prompt])

        if response and response.text:
            # Extract JSON from response
            json_match = re.search(r"{.*}", response.text, re.DOTALL)
            if json_match:
                return {"success": True, "error": None, "text": json_match.group(0)}

        return {"success": False, "error": "Failed to extract valid JSON", "text": None}

    except Exception as e:
        return {"success": False, "error": str(e), "text": None}

    # def get_valid_mark(mark):
    #     """Convert mark to nearest valid value (0, 5, or 8)."""
    #     try:
    #         mark = int(mark)
    #         if mark in [0, 5, 8]:
    #             return mark
    #         elif mark < 3:
    #             return 0
    #         elif mark < 6.5:
    #             return 5
    #         else:
    #             return 8
    #     except (ValueError, TypeError):
    #         return 0

    # def extract_data_to_json(text):
    """Convert extracted text to JSON format."""
    try:
        if not text:
            return None

        # Initialize data structure
        data = {
            "roll_number": "000000000000",
            "questions": {
                f"Q{i}": {"a": 0, "b": 0, "c": 0, "d": 0} for i in range(1, 7)
            },
            "total_marks": 0,
        }

        # Process text line by line
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extract roll number
            if line.startswith("Roll No:"):
                roll_no = "".join(filter(str.isdigit, line))
                if len(roll_no) >= 12:
                    data["roll_number"] = roll_no[:12]

            # Extract marks
            elif line.startswith("Q"):
                try:
                    q_num = line[1]
                    if not q_num.isdigit() or int(q_num) < 1 or int(q_num) > 6:
                        continue

                    # Extract marks without brackets
                    marks = line.split(":")[1].strip().split()
                    if len(marks) == 4:
                        q_key = f"Q{q_num}"
                        data["questions"][q_key] = {
                            "a": get_valid_mark(marks[0]),
                            "b": get_valid_mark(marks[1]),
                            "c": get_valid_mark(marks[2]),
                            "d": get_valid_mark(marks[3]),
                        }
                except (IndexError, ValueError) as e:
                    print(f"Error parsing line '{line}': {e}")
                    continue

        # Calculate total marks
        total = sum(
            mark for q_data in data["questions"].values() for mark in q_data.values()
        )
        data["total_marks"] = total

        print(f"Processed JSON Data:\n{data}")  # Debug print
        return data

    except Exception as e:
        print(f"Error converting to JSON: {e}")
        return None
