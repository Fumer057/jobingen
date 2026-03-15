import os
import json
import google.generativeai as genai
from openai import OpenAI
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

def generate_schema(prompt: str, api_key: str, provider: str = "gemini") -> Dict[str, str]:
    """
    Converts a natural language prompt into a JSON schema using either Gemini or OpenAI.
    """
    system_prompt = """
    Convert the following data extraction request into a simple JSON schema.
    The keys should be snake_case representatons of the fields.
    The values should always be "string".
    Return ONLY valid JSON.
    
    User Request: {prompt}
    """
    
    if provider.lower() == "gemini":
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(system_prompt.format(prompt=prompt))
        text = response.text.strip()
    else:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": system_prompt.format(prompt=prompt)}],
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content.strip()
    
    # Strip potential markdown blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        
    return json.loads(text)
