import os
import json
from openai import OpenAI
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class SchemaAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_schema(self, prompt: str) -> Dict[str, str]:
        """
        Converts a natural language prompt into a JSON schema using OpenAI.
        """
        system_prompt = """
        Convert the following data extraction request into a simple JSON schema.
        The keys should be snake_case representatons of the fields.
        The values should always be "string".
        Return ONLY valid JSON.
        
        User Request: {prompt}
        """
        
        response = self.client.chat.completions.create(
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
