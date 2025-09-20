from pydantic import BaseModel
from datetime import datetime

class PromptRequest(BaseModel):
    """Defines the shape for the AI prompt request."""
    prompt: str

class WidgetCreate(BaseModel):
    """Defines the data structure the AI must return to create a widget."""
    name: str
    category: str
    python_code: str
    html_code: str

class Widget(WidgetCreate):
    """Defines the data for a widget after it's been saved to the database."""
    id: int
    creation_date: datetime
    usage_count: int

    class Config:
        from_attributes = True