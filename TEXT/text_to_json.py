import google.generativeai as genai
import re
import json
import time
from dotenv import load_dotenv
import os
from typing import Dict, Optional
from PIL import Image

# Load environment variables
load_dotenv()


# Configure the Gemini API
API_KEY = os.getenv("API_KEY")
genai.configure(api_key=API_KEY)


def process_text_with_image(extracted_text, image_path):
    """Process text with image context for more accurate extraction."""
    try:
        # Parse the extracted JSON
        if isinstance(extracted_text, str):
            data = json.loads(extracted_text)
        else:
            data = extracted_text

        # Initialize result structure
        result = {
            "roll_number": "",
            "questions": {
                f"Q{i}": {"a": 0, "b": 0, "c": 0, "d": 0} for i in range(1, 7)
            },
            "total_marks": 0,
        }

        # Extract roll number
        result["roll_number"] = data.get("roll_number", "")

        # Extract questions data
        if "questions" in data:
            for q_num in range(1, 7):
                q_key = f"Q{q_num}"
                if q_key in data["questions"]:
                    q_data = data["questions"][q_key]
                    result["questions"][q_key] = {
                        part: (
                            int(mark)
                            if isinstance(mark, (int, str)) and str(mark).isdigit()
                            else 0
                        )
                        for part, mark in q_data.items()
                    }

        # Extract total marks
        total = data.get("total_marks", 0)
        result["total_marks"] = (
            int(total) if isinstance(total, (int, str)) and str(total).isdigit() else 0
        )

        # Validate marks
        for q_data in result["questions"].values():
            for part, mark in q_data.items():
                if not (0 <= mark <= 8):
                    q_data[part] = 0

        return result

    except Exception as e:
        print(f"Error processing text: {e}")
        return None


# class AnswerSheetParser:
#     def __init__(self):
#         self.valid_marks = {0, 5, 8}

#     def parse_text(self, text: str) -> Optional[Dict]:
#         """Parse extracted text into structured data."""
#         try:
#             # Extract roll number
#             roll_match = re.search(r'Roll No\s*:?\s*(\d{12})', text, re.IGNORECASE)
#             if not roll_match:
#                 print("No valid 12-digit roll number found")
#                 return None
#             roll_number = roll_match.group(1)

#             # Initialize questions data
#             questions = {
#                 f'Q{q}': {'a': 0, 'b': 0, 'c': 0, 'd': 0}
#                 for q in range(1, 7)
#             }

#             # Extract marks
#             # Look for patterns like "Q1a: 5" or "1a. 5" or "Box 1: 5 (Q1a)"
#             patterns = [
#                 r'Q(\d)([a-d])\s*:?\s*(\d+)',
#                 r'(\d)([a-d])\.\s*(\d+)',
#                 r'Box\s*\d+\s*:\s*(\d+)\s*\(Q(\d)([a-d])\)'
#             ]

#             marks_found = False
#             for pattern in patterns:
#                 matches = re.finditer(pattern, text)
#                 for match in matches:
#                     if pattern.startswith('Box'):
#                         mark = int(match.group(1))
#                         q_num = match.group(2)
#                         part = match.group(3)
#                     else:
#                         q_num = match.group(1)
#                         part = match.group(2)
#                         mark = int(match.group(3))

#                     if mark in self.valid_marks:
#                         questions[f'Q{q_num}'][part] = mark
#                         marks_found = True

#             if not marks_found:
#                 print("No valid marks found")
#                 return None

#             # Calculate total
#             total_marks = sum(
#                 mark
#                 for q_data in questions.values()
#                 for mark in q_data.values()
#             )

#             return {
#                 'roll_number': roll_number,
#                 'questions': questions,
#                 'total_marks': total_marks
#             }

#         except Exception as e:
#             print(f"Error parsing text: {e}")
#             return None

#     def format_output(self, data: Optional[Dict]) -> str:
#         """Format the parsed data as JSON string."""
#         if not data:
#             return "No valid data to format"
#         return json.dumps(data, indent=2)

# def extract_data_to_json(text):
#     """Extract structured data from text and convert to JSON format."""
#     try:
#         # Initialize dictionary to store extracted data
#         data = {
#             'roll_no': None,
#             'marks': {
#                 'Q1': {'a': 0, 'b': 0, 'c': 0, 'd': 0},
#                 'Q2': {'a': 0, 'b': 0, 'c': 0, 'd': 0},
#                 'Q3': {'a': 0, 'b': 0, 'c': 0, 'd': 0},
#                 'Q4': {'a': 0, 'b': 0, 'c': 0, 'd': 0},
#                 'Q5': {'a': 0, 'b': 0, 'c': 0, 'd': 0},
#                 'Q6': {'a': 0, 'b': 0, 'c': 0, 'd': 0}
#             }
#         }

#         # Split text into lines
#         lines = text.strip().split('\n')

#         # Extract roll number
#         for line in lines:
#             if 'Roll No:' in line:
#                 data['roll_no'] = line.split(':')[1].strip()
#                 break

#         # Extract marks
#         current_question = None
#         for line in lines:
#             if line.startswith('Q') and ':' in line:
#                 # Get question number and marks
#                 q_parts = line.split(':')
#                 current_question = q_parts[0].strip()  # Q1, Q2, etc.

#                 # Get marks for this question
#                 marks = q_parts[1].strip().split()
#                 if len(marks) == 4:  # Ensure we have all 4 parts
#                     data['marks'][current_question] = {
#                         'a': int(marks[0]),
#                         'b': int(marks[1]),
#                         'c': int(marks[2]),
#                         'd': int(marks[3])
#                     }

#         return data

#     except Exception as e:
#         print(f"Error extracting data: {e}")
#         return None

# def format_json_output(data):
#     """Format the JSON data for better readability."""
#     try:
#         if not data:
#             return None

#         # Calculate total marks
#         total = sum(
#             mark
#             for question in data['marks'].values()
#             for mark in question.values()
#         )

#         formatted_data = {
#             'roll_no': data['roll_no'],
#             'marks_by_question': data['marks'],
#             'total_marks': total
#         }

#         return formatted_data

#     except Exception as e:
#         print(f"Error formatting JSON: {e}")
#         return None

# # Test function to verify extraction
# def test_extraction(text):
#     """Test the extraction with sample text"""
#     parser = AnswerSheetParser()
#     result = parser.parse_text(text)
#     if result:
#         print("\nExtracted Data:")
#         print(parser.format_output(result))
#     else:
#         print("Failed to extract data")

# # Example usage
# if __name__ == "__main__":
# sample_text = """
# Roll No: 123456789012
# Marks Awarded:
# Q1a: 5 Q1b: 0 Q1c: 8 Q1d: 5
# Q2a: 5 Q2b: 8 Q2c: 0 Q2d: 5
# Q3a: 8 Q3b: 5 Q3c: 5 Q3d: 0
# """
# test_extraction(sample_text)
