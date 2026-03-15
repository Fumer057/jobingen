import os
import google.generativeai as genai
from openai import OpenAI
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

def find_next_page(content: str, current_url: str, api_key: str, provider: str = "gemini") -> Optional[str]:
    """
    Uses LLM to identify the URL for the 'next' page from the current page content.
    """
    prompt = f"""
    Analyze the following markdown content of a webpage and find the URL for the next page of results (pagination).
    Current URL: {current_url}
    
    Return ONLY the absolute URL. If no next page link is found, return "None".
    
    PAGE CONTENT:
    {content[:10000]}
    """
    
    if provider.lower() == "gemini":
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        url = response.text.strip()
    else:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        url = response.choices[0].message.content.strip()
    
    if url.lower() == "none" or "none" in url.lower():
        return None
    return url
