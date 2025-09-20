import os
import shutil
import tempfile
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List

from . import ai_integration, widget_runner, db, models

# --- STARTUP CONFIGURATION ---
print("Initializing AI Widget Generation Backend...")
os.makedirs("uploads", exist_ok=True)
db.setup_storage() # This sets up the required directories.

app = FastAPI(
    title="AI Widget Generation API",
    description="Backend to generate, store, and execute AI-created widgets.",
    version="1.0.0"
)

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- API ENDPOINTS ---

@app.post("/generate_widget", response_model=models.Widget, tags=["Widgets"])
def generate_widget_endpoint(request: models.PromptRequest):
    """
    Orchestrates the entire widget creation flow.
    """
    print(f"Received request to generate widget for prompt: '{request.prompt}'")
    try:
        # Step 1: Get the schema of the DATA database to give context to the AI.
        schema = db.get_data_db_schema()
        
        # Step 2: Call the AI with the user's prompt AND the database schema.
        ai_output = ai_integration.get_widget_code_from_gemini(request.prompt, schema)
        widget_data = models.WidgetCreate(**ai_output)
        
        # Step 3: Save the new widget's data to a JSON file.
        new_widget = db.create_widget(widget_data)
        print(f"Widget '{new_widget.name}' data saved to JSON with ID: {new_widget.id}")
        
        return new_widget
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {e}")

@app.get("/get_widgets", response_model=List[models.Widget], tags=["Widgets"])
def get_widgets_endpoint():
    """Provides the frontend with a list of all created widgets from JSON files."""
    return db.get_all_widgets()

@app.get("/get_widget/{widget_id}", response_model=models.Widget, tags=["Widgets"])
def get_widget_endpoint(widget_id: int):
    """Provides the full data for one widget, needed for the expansion view."""
    widget = db.get_widget_by_id(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail=f"Widget with ID {widget_id} not found.")
    return widget

@app.post("/run_widget/{widget_id}", tags=["Execution"])
async def run_widget_endpoint(widget_id: int, request: Request):
    """Executes a widget's code, loaded from its JSON file, with user-provided data."""
    inputs = {}
    temp_file_paths = []
    
    widget = db.get_widget_by_id(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail="Widget data not found.")

    # Create a temporary file to execute the code
    temp_py_file = None
    try:
        # Create a named temporary file that widget_runner can import
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as temp_py_file:
            temp_py_file.write(widget.python_code)
            temp_py_path = temp_py_file.name
        
        form_data = await request.form()
        for key, value in form_data.items():
            if hasattr(value, "filename") and value.filename: # Check if it is a file upload
                # Ensure the uploads directory exists
                os.makedirs("uploads", exist_ok=True)
                temp_file_path = f"uploads/{value.filename}"
                temp_file_paths.append(temp_file_path)
                with open(temp_file_path, "wb") as buffer:
                    shutil.copyfileobj(value.file, buffer)
                inputs[key] = temp_file_path # Pass the file path to the widget
            else:
                inputs[key] = value
        
        result = widget_runner.execute_widget_code(temp_py_path, inputs)
        db.increment_usage_count(widget_id)
        
        return JSONResponse(content={"output": str(result)})
    except Exception as e:
        # Provide more detailed error logging on the backend
        import traceback
        print(f"ERROR running widget {widget_id}: {e}")
        traceback.print_exc()
        return JSONResponse(content={"error": f"An error occurred during execution: {e}"}, status_code=500)
    finally:
        # Clean up the temporary python file
        if temp_py_file and os.path.exists(temp_py_file.name):
            os.remove(temp_py_file.name)
        # Clean up any uploaded files
        for path in temp_file_paths:
            if os.path.exists(path):
                os.remove(path)