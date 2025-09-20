import os
import json
import google.generativeai as genai

def get_widget_code_from_gemini(user_prompt: str, schema: str) -> dict:
    """
    Generates a full Python+HTML widget from a user prompt and database schema.
    Can create widgets for DB queries, plotting, calculations, or image manipulation.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)

    system_prompt = f"""
    You are an expert AI that creates self-contained Python and HTML widgets.
    Your sole output must be a single, valid JSON object with the keys "name", "category", "python_code", and "html_code".

    You can create four types of widgets:
    1.  DATABASE QUERY: For fetching and displaying data from a database.
    2.  PLOTTING: For creating visual graphs from database data.
    3.  IMAGE MANIPULATION: For editing a user-uploaded image.
    4.  GENERAL: For calculators or tools that don't need a database or files.

    DATABASE CONTEXT (for DB Query and Plotting widgets ONLY):
    If the user asks to query or plot data, you MUST use the following database schema.
    The database is located at `database/widgets.db`.
    --- SCHEMA START ---
    {schema}
    --- SCHEMA END ---

    RULES FOR "python_code":
    1.  It MUST contain a single function: `def run_widget(inputs: dict) -> str:`.
    2.  The `inputs` dictionary contains values from the HTML form.

    SPECIFIC INSTRUCTIONS BY WIDGET TYPE:
    -   For **DATABASE QUERY**:
        - Connect to `database/widgets.db` and execute a `SELECT` query.
        - Format the result into a human-readable string. Return "No results found." if empty.
    -   For **GENERAL (e.g., calculator)**:
        - Do NOT connect to a database or read files.
        - Perform calculations using only the `inputs` dictionary and return the result as a string.
    -   For **PLOTTING**:
        - Connect to `database/widgets.db` to get data.
        - Use 'matplotlib' and 'pandas' to generate a plot.
        - Return the plot as a Base64 encoded string: `data:image/png;base64,YOUR_BASE64_STRING`.
    -   For **IMAGE MANIPULATION**:
        - You MUST use the `Pillow` library (e.g., `from PIL import Image, ImageDraw, ImageFont`).
        - The `inputs` dictionary will contain the file path to the user's uploaded image (e.g., `inputs['user_image']`).
        - Open the image, perform the requested manipulations.
        - Return the final image as a Base64 encoded string: `data:image/png;base64,YOUR_BASE64_STRING`.

    RULES FOR "html_code":
    1.  For IMAGE MANIPULATION, you MUST include `<input type="file" name="user_image" required>`.
    2.  For other types needing input, use appropriate `<input>` tags.
    3.  If no user input is needed, provide a simple message like "<p>Click Run to see the latest data.</p>".
    4.  MUST include a submit button: `<button type="submit">Run</button>`.

    - "name": A short, descriptive name (e.g., "Platinum Member Lookup", "Add Banner to Image").
    - "category": Choose ONE: "query", "numerical", "graphs", "image", "records".
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
    
    print(f"Sending prompt to Gemini API for widget generation: '{user_prompt}'")
    try:
        response = model.generate_content([system_prompt, user_prompt])
        parsed_json = json.loads(response.text)
        required_keys = ["name", "category", "python_code", "html_code"]
        if not all(key in parsed_json for key in required_keys):
            raise ValueError("AI response is missing required keys.")
        
        print("Successfully received and validated widget code from Gemini API.")
        return parsed_json
    except Exception as e:
        print(f"ERROR: An error occurred with the Gemini API - {e}")
        raise ValueError(f"Failed to generate widget from AI: {e}")