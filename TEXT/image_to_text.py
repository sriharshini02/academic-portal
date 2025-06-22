import cv2
import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv
import re
import json  # Import json module

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.getenv("API_KEY")
genai.configure(api_key=API_KEY)  # type: ignore


# Helper function to get a valid mark (now properly placed and used)
def get_valid_mark(mark: str) -> float:
    """Convert mark to nearest valid float value."""
    try:
        # Convert to float and round to 1 decimal place
        mark_float = float(mark)
        return round(mark_float, 1)
    except (ValueError, TypeError):
        return 0.0  # Return float 0.0 for invalid marks


# Helper function to extract and structure data from raw text (now properly placed and used)
def extract_data_to_json(text: str) -> dict | None:
    """Convert raw extracted text to a structured JSON dictionary."""
    if not text:
        return None

    # --- Step 1: Try to extract JSON from a markdown code block or direct JSON string ---
    json_str = text.strip()

    # Look for a markdown JSON block (e.g., ```json\n{...}\n```)
    json_code_block_match = re.search(r"```json\s*({.*?})\s*```", json_str, re.DOTALL)
    if json_code_block_match:
        json_str = json_code_block_match.group(1)
        print("Extracted JSON from markdown code block.")
    else:
        # Fallback: Find the first '{' and the last '}' to get a potential JSON substring
        first_brace = json_str.find("{")
        last_brace = json_str.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = json_str[first_brace : last_brace + 1]
            print("Extracted JSON string by finding first '{' and last '}'.")
        else:
            print(
                "Could not find a clear JSON structure using braces/markdown. Attempting regex on full text."
            )

    try:
        parsed_data = json.loads(json_str)
        # Basic validation that it contains the expected top-level keys
        if (
            "roll_number" in parsed_data
            and "questions" in parsed_data
            and "total_marks" in parsed_data
        ):
            # Ensure marks are floats
            if "questions" in parsed_data and isinstance(
                parsed_data["questions"], dict
            ):
                for q_key, q_parts in parsed_data["questions"].items():
                    if isinstance(q_parts, dict):
                        for part_key, mark_value in q_parts.items():
                            parsed_data["questions"][q_key][part_key] = get_valid_mark(
                                str(mark_value)
                            )
            if "total_marks" in parsed_data:
                parsed_data["total_marks"] = get_valid_mark(
                    str(parsed_data["total_marks"])
                )
            print(f"Successfully parsed direct JSON: {parsed_data}")
            return parsed_data
        else:
            print(
                "Parsed JSON missing expected top-level keys: roll_number, questions, or total_marks. Falling back to regex."
            )

    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}. Falling back to regex parsing on original text.")
    except Exception as e:
        print(f"Error during initial JSON parsing: {e}. Falling back to regex parsing.")

    # --- Step 2: Fallback to regex parsing if direct JSON parsing fails or is incomplete ---
    data = {
        "roll_number": "",
        "questions": {
            f"Q{i}": {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0} for i in range(1, 7)
        },
        "total_marks": 0.0,
    }

    # Process text line by line using original full response text
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract roll number (more flexible regex)
        roll_match = re.search(
            r"(?:Roll No|Roll Number|Student ID):\s*([A-Za-z0-9]+)", line, re.IGNORECASE
        )
        if roll_match:
            data["roll_number"] = roll_match.group(1).strip()
            continue

        # Extract marks for questions (more flexible regex for parts)
        # Tries to capture Q#, then finds 'a=', 'b=', 'c=', 'd=' and their values
        q_match = re.search(
            r"Q(\d+):\s*(?:(?:a=(\d+\.?\d*))?)\s*(?:(?:b=(\d+\.?\d*))?)\s*(?:(?:c=(\d+\.?\d*))?)\s*(?:(?:d=(\d+\.?\d*))?)",
            line,
            re.IGNORECASE,
        )
        if q_match:
            q_num = int(q_match.group(1))
            if 1 <= q_num <= 6:
                q_key = f"Q{q_num}"
                data["questions"][q_key] = {
                    "a": get_valid_mark(q_match.group(2) or "0.0"),
                    "b": get_valid_mark(q_match.group(3) or "0.0"),
                    "c": get_valid_mark(q_match.group(4) or "0.0"),
                    "d": get_valid_mark(q_match.group(5) or "0.0"),
                }
            continue

        # Try to extract total marks if it appears on its own line (more flexible regex)
        total_marks_match = re.search(
            r"(?:Total marks|Total):\s*(\d+\.?\d*)", line, re.IGNORECASE
        )
        if total_marks_match:
            data["total_marks"] = get_valid_mark(total_marks_match.group(1))
            continue

    # If total_marks wasn't explicitly found, calculate from extracted questions
    if data["total_marks"] == 0.0:
        calculated_total = sum(
            mark for q_data in data["questions"].values() for mark in q_data.values()
        )
        data["total_marks"] = round(calculated_total, 1)

    print(f"Parsed Data (after regex fallback): {data}")
    return data


def extract_text_from_image(image_path: str) -> dict | None:
    """Extract text from image using Gemini API and return structured JSON."""
    try:
        # Use 'with' statement for proper file handling and to avoid file locking
        with Image.open(image_path) as image_part:
            # Configure Gemini
            generation_config = {
                "temperature": 0.1,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 2048,
            }

            # Initialize model
            model = genai.GenerativeModel(  # type: ignore
                model_name="gemini-2.0-flash", generation_config=generation_config  # type: ignore
            )

            # Create focused prompt for mark extraction - Emphasize strict JSON format
            prompt = """
            Analyze this answer sheet image and extract ONLY the following information.
            Return the data STRICTLY in JSON format, without any additional text or markdown formatting (e.g., no ```json at start).
            
            Extract:
            1.  "roll_number": The Roll Number (e.g., "A23126551134").
            2.  "questions": An object where each key is a question number (e.g., "Q1", "Q2") and its value is an object containing "a", "b", "c", "d" parts with their marks as numbers (float, e.g., 5.0). If a part has no marks, use 0.0. Example: {"a": 5.0, "b": 3.5, "c": 0.0, "d": 2.0}.
            3.  "total_marks": The overall total marks from the sheet as a number (float, e.g., 23.0).

            Example JSON structure (ensure your output matches this EXACTLY, including all Q1-Q6 keys even if empty):
            {
                "roll_number": "A23126551134",
                "questions": {
                    "Q1": {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0},
                    "Q2": {"a": 5.0, "b": 5.0, "c": 0.0, "d": 0.0},
                    "Q3": {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0},
                    "Q4": {"a": 5.0, "b": 8.0, "c": 0.0, "d": 0.0},
                    "Q5": {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0},
                    "Q6": {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}
                },
                "total_marks": 23.0
            }
            
            Focus only on extracting the specified numerical values and the exact roll number. Do not include any introductory or concluding sentences.
            """

            # Generate response
            response = model.generate_content([image_part, prompt])

            if response and response.text:
                print(f"Raw Gemini API Response Text:\n{response.text}")  # Debug print
                return extract_data_to_json(response.text)
            else:
                print("Gemini API returned no response text.")
                return None

    except Exception as e:
        print(
            f"Error in extract_text_from_image (Gemini API call or image processing): {e}"
        )
        return None
