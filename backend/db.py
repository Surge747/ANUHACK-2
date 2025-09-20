import sqlite3
import json
import os
import time
from datetime import datetime
from . import models

# --- CONFIGURATION ---
# The single database for application data (members, sales, etc.)
DATA_DB_FILE = "database/widgets.db"
# Directory to store widget definitions as JSON files
WIDGETS_DIR = "widgets"


def setup_storage():
    """
    Initializes the application's storage directories.
    - Ensures the 'database/' directory exists for the user-provided DB.
    - Ensures the 'widgets/' directory exists for JSON widget files.
    NOTE: This function ASSUMES 'database/widgets.db' is provided and populated.
    It does not create tables or add data.
    """
    print("Setting up storage directories...")
    os.makedirs("database", exist_ok=True)
    os.makedirs(WIDGETS_DIR, exist_ok=True)
    print(f"Storage directory '{WIDGETS_DIR}' is ready.")
    print("Assuming 'database/widgets.db' is provided.")


def create_widget(widget_data: models.WidgetCreate) -> models.Widget:
    """Saves a new widget as a JSON file in the widgets/ directory."""
    widget_id = int(time.time() * 1000)
    new_widget = models.Widget(
        id=widget_id,
        creation_date=datetime.utcnow(),
        usage_count=0,
        **widget_data.model_dump()
    )
    
    file_path = os.path.join(WIDGETS_DIR, f"{widget_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(new_widget.model_dump(mode='json'), f, indent=4)
        
    print(f"Widget '{new_widget.name}' saved to {file_path}")
    return new_widget

def get_widget_by_id(widget_id: int) -> models.Widget | None:
    """Retrieves a single widget by its ID from a JSON file."""
    file_path = os.path.join(WIDGETS_DIR, f"{widget_id}.json")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return models.Widget(**data)

def get_all_widgets() -> list[models.Widget]:
    """Retrieves all widgets from the JSON files in the widgets/ directory."""
    widgets = []
    if not os.path.exists(WIDGETS_DIR):
        return []
    for filename in sorted(os.listdir(WIDGETS_DIR), reverse=True):
        if filename.endswith(".json"):
            file_path = os.path.join(WIDGETS_DIR, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    widgets.append(models.Widget(**data))
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Warning: Could not parse {filename}: {e}")
    return widgets

def increment_usage_count(widget_id: int):
    """Increments the usage_count for a specific widget in its JSON file."""
    widget = get_widget_by_id(widget_id)
    if not widget:
        return
    
    widget.usage_count += 1
    file_path = os.path.join(WIDGETS_DIR, f"{widget_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(widget.model_dump(mode='json'), f, indent=4)


def get_data_db_schema() -> str:
    """
    Introspects the DATA database and returns the CREATE TABLE statements.
    This provides the necessary context for the AI to write accurate queries.
    """
    print("Fetching DATA database schema for AI context...")
    if not os.path.exists(DATA_DB_FILE):
        raise ValueError(f"Database file not found at '{DATA_DB_FILE}'. Please provide the database.")
    try:
        db_uri = f"file:{DATA_DB_FILE}?mode=ro"
        with sqlite3.connect(db_uri, uri=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            schema_parts = [row[1] for row in cursor.fetchall()]
            if not schema_parts:
                raise ValueError(f"No tables found in the database '{DATA_DB_FILE}'.")
        full_schema = "\n\n".join(schema_parts)
        print("Schema fetched successfully.")
        return full_schema
    except sqlite3.Error as e:
        print(f"ERROR: Failed to get database schema - {e}")
        raise ValueError(f"Could not retrieve database schema: {e}")