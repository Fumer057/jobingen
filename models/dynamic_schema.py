from pydantic import create_model
from typing import Optional, Type, Dict, Any

def create_dynamic_model(name: str, schema: Dict[str, str]) -> Type:
    """
    Creates a Pydantic model dynamically based on a dictionary of field names and types (as strings).
    Currently maps all requested fields to Optional[str] for maximum flexibility.
    """
    fields = {}
    for key in schema:
        # We assume all fields are Optional[str] for simplicity in extraction
        fields[key] = (Optional[str], None)
        
    DynamicModel = create_model(name, **fields)
    return DynamicModel
