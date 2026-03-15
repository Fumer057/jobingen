import streamlit as st
import asyncio
import os
import time
from dotenv import load_dotenv
from crawler.crawler_engine import crawl_page
from agents.schema_agent import generate_schema
from models.dynamic_schema import create_dynamic_model
from agents.extraction_agent import extract_data
from utils.exporter import export_to_csv, export_to_json
from utils.pagination import find_next_page
import pandas as pd
import sys

# Windows-specific fix for Playwright and asyncio
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

st.set_page_config(page_title="Universal AI Web Scraper", page_icon="🕷️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; transition: 0.3s; }
    .stButton>button:hover { background-color: #ff3333; transform: scale(1.02); }
    </style>
    """, unsafe_allow_html=True)

st.title("🕷️ Universal AI Web Scraper")
st.markdown("### Powered by Gemini 2.0 & GPT-4o-mini")

with st.sidebar:
    st.header("⚙️ Configuration")
    provider = st.selectbox("LLM Provider", ["Gemini", "OpenAI"])
    
    if provider == "Gemini":
        api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    else:
        api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        
    st.divider()
    st.header("💸 Save Credits")
    use_manual_schema = st.checkbox("Manual Schema (Skip AI Schema Gen)", value=False)
    manual_schema_input = "{}"
    if use_manual_schema:
        manual_schema_input = st.text_area("Enter JSON Schema", value='{"title": "string", "price": "string"}', height=100)
    
    enable_pagination = st.checkbox("Enable Pagination (Extra LLM Call)", value=False)
    st.info("💡 Pro Tip: Disable pagination and use manual schema to minimize API costs by 2x.")

col1, col2 = st.columns([1, 1])

with col1:
    url = st.text_input("Target URL", placeholder="https://example.com")
    prompt_input = st.text_area("Extraction Instructions", 
                         placeholder="e.g., Extract job title, company name, location and salary",
                         value="Extract job title, company name, location and salary")
    max_pages = st.number_input("Max Pages", min_value=1, max_value=5, value=1, disabled=not enable_pagination)

if st.button("🚀 Start AI Extraction"):
    if not url or (not prompt_input and not use_manual_schema) or not api_key:
        st.error("Missing required inputs.")
    else:
        async def run_scraper():
            all_extracted_data = []
            current_url = url
            
            with st.status("Extracting Data...", expanded=True) as status:
                try:
                    # 1. Get Schema
                    if use_manual_schema:
                        import json
                        schema = json.loads(manual_schema_input)
                        status.update(label="✅ Using Manual Schema (Skipped AI step)")
                    else:
                        status.update(label="🤖 GPT/Gemini: Designing Data Schema...")
                        schema = generate_schema(prompt_input, api_key, provider.lower())
                    
                    st.write("**Data Schema:**", schema)
                    
                    # 2. Create Model
                    DynamicModel = create_dynamic_model("ExtractionResult", schema)
                    
                    for p in range(int(max_pages)):
                        status.update(label=f"🌐 Crawling Page {p+1}...")
                        markdown = await crawl_page(current_url)
                        
                        status.update(label=f"🧠 LLM: Extracting data...")
                        page_results = extract_data(markdown, DynamicModel, api_key, prompt_input, provider.lower())
                        
                        if page_results:
                            all_extracted_data.extend(page_results)
                            st.write(f"✅ Found {len(page_results)} items on Page {p+1}")
                        
                        if enable_pagination and p < max_pages - 1:
                            status.update(label="🔗 Searching for next page link...")
                            next_url = find_next_page(markdown, current_url, api_key, provider.lower())
                            if next_url and next_url != current_url:
                                current_url = next_url
                                time.sleep(1)
                            else:
                                break
                        elif not enable_pagination:
                            break
                    
                    status.update(label="✨ Process Complete!", state="complete")
                    
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        st.error("📉 Rate Limit Hit! Your API quota has been exhausted. Please wait a few minutes or switch to another provider (e.g., OpenAI).")
                    else:
                        st.error(f"❌ An error occurred: {e}")
                    status.update(label="Failed", state="error")
            
            if all_extracted_data:
                st.success(f"Successfully extracted {len(all_extracted_data)} total items!")
                df = pd.DataFrame(all_extracted_data)
                st.dataframe(df, use_container_width=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    csv_path = export_to_csv(all_extracted_data)
                    with open(csv_path, "rb") as f:
                        st.download_button("📥 Download CSV", f, "extracted_data.csv", "text/csv")
                with c2:
                    json_path = export_to_json(all_extracted_data)
                    with open(json_path, "rb") as f:
                        st.download_button("📥 Download JSON", f, "extracted_data.json", "application/json")

        # Robust loop management for Windows + Streamlit + Playwright
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_scraper())
        finally:
            loop.close()
