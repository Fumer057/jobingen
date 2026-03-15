import os
import google.generativeai as genai
from openai import OpenAI
import json
from typing import List, Type, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

def extract_data(content: str, model_class: Type[BaseModel], api_key: str, user_prompt: str = "", provider: str = "gemini") -> List[Dict[str, Any]]:
    """
    Extracts structured data as a LIST of objects using Gemini or OpenAI.
    """
    fields = model_class.model_fields
    schema_desc = ", ".join([f"{name} (string)" for name in fields.keys()])
    
    prompt = f"""
    EXTRACT DATA FROM TEXT:
    User Instruction: {user_prompt}
    Schema: {schema_desc}
    Format: JSON List of objects
    Rules: 
    - Use null for missing fields.
    - Return ONLY the JSON list.
    
    TEXT:
    {content[:12000]}
    """
    
    if provider.lower() == "gemini":
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
    else:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"} # Some models might return a wrapper list
        )
        text = response.choices[0].message.content.strip()
    
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(text)
        
        # If OpenAI json_object mode was used, it might be wrapped in a key
        if isinstance(data, dict):
            # Look for the first list value
            for val in data.values():
                if isinstance(val, list):
                    data = val
                    break
            else:
                data = [data]
        
        if not isinstance(data, list):
            data = [data]
            
        validated_data = []
        for item in data:
            try:
                validated_item = model_class.model_validate(item).model_dump()
                validated_data.append(validated_item)
            except Exception:
                continue
                
        return validated_data
    except Exception as e:
        raise Exception(f"Extraction failed: {str(e)}")
