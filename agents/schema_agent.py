import os
import json
import google.generativeai as genai
from openai import OpenAI
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class SchemaAgent:
    def __init__(self, provider: str = "openai", api_key: str = None):
        self.provider = provider.lower()
        self.api_key = api_key or (os.getenv("GEMINI_API_KEY") if provider == "gemini" else os.getenv("OPENAI_API_KEY"))
        
        if self.provider == "gemini":
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.client = OpenAI(api_key=self.api_key)

    def generate_schema(self, prompt: str) -> Dict[str, str]:
        """
        Converts a natural language prompt into a JSON schema.
        """
        system_prompt = """
        Convert the following data extraction request into a simple JSON schema.
        The keys should be snake_case representatons of the fields.
        The values should always be "string".
        Return ONLY valid JSON.
        
        User Request: {prompt}
        """
        
        if self.provider == "gemini":
            response = self.model.generate_content(system_prompt.format(prompt=prompt))
            text = response.text.strip()
        else:
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
