import pandas as pd
import json
from typing import List, Dict, Any

def export_csv(data: List[Dict[str, Any]], filename: str = "extracted_data.csv"):
    """
    Exports a list of dictionaries to a CSV file.
    """
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    return filename

def export_json(data: List[Dict[str, Any]], filename: str = "extracted_data.json"):
    """
    Exports a list of dictionaries to a JSON file.
    """
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    return filename

# Backwards compatibility names
export_to_csv = export_csv
export_to_json = export_json
