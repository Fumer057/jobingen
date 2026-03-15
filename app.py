import streamlit as st
import asyncio
import time
import os
import nest_asyncio
from dotenv import load_dotenv

from crawler.crawler_engine import WebCrawler
from agents.schema_agent import SchemaAgent
from agents.extraction_agent import ExtractionAgent
from agents.pagination_agent import PaginationAgent
from models.dynamic_schema import create_dynamic_model
from utils.chunker import split_text
from utils.exporter import export_csv, export_json

# ── Load env vars ────────────────────────────────────────────────────────────
load_dotenv()

# ── Fix asyncio conflict with Streamlit (Python 3.10+ safe) ─────────────────
nest_asyncio.apply()

# ── UI ───────────────────────────────────────────────────────────────────────
st.title("🕷️ Universal AI Web Scraper")

with st.sidebar:
    st.header("⚙️ Configuration")
    provider = st.selectbox("LLM Provider", ["Gemini", "OpenAI"])
    
    if provider == "Gemini":
        api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
        model_name = "gemini-2.0-flash"
    else:
        api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        model_name = "gpt-4o-mini"

    st.divider()
    st.info(f"Using {model_name}")

if not api_key or api_key.startswith("your_"):
    st.warning(f"⚠️ Please enter a valid {provider} API Key in the sidebar.")
    st.stop()

url = st.text_input("Enter URL", placeholder="https://books.toscrape.com")

user_prompt = st.text_area(
    "Describe what data you want",
    "Extract product name, price and rating"
)

max_pages = st.slider("Max pages to scrape", min_value=1, max_value=10, value=2)

# ── Main pipeline ────────────────────────────────────────────────────────────
if st.button("Scrape") and url:

    # Reset state on every fresh Scrape click
    for key in ("schema", "schema_confirmed"):
        st.session_state.pop(key, None)

    schema_agent    = SchemaAgent(provider=provider.lower(), api_key=api_key)
    extraction_agent = ExtractionAgent(provider=provider.lower(), api_key=api_key)
    pagination_agent = PaginationAgent()

    # Step 1 — generate schema
    with st.spinner("Generating schema from your prompt..."):
        schema = schema_agent.generate_schema(user_prompt)
        st.session_state["schema"] = schema

    st.write("### 🗂️ Generated Schema")
    st.json(schema)

    DynamicModel = create_dynamic_model("ExtractionResult", schema)

    # Step 2 — crawl + extract
    crawler = WebCrawler()

    async def run():
        await crawler.start()

        data = []
        current_url = url
        pages_scraped = 0

        while current_url and pages_scraped < max_pages:

            st.write(f"📄 Scraping page {pages_scraped + 1}: `{current_url}`")

            try:
                result = await crawler.fetch_page(current_url)
            except Exception as e:
                st.error(f"Failed to load page: {e}")
                break

            text = result["text"]
            html = result["html"]
            chunks = split_text(text)

            st.write(f"   ↳ {len(chunks)} chunks to process")

            rate_display = st.empty()

            for i, chunk in enumerate(chunks):
                # Show live rate limit usage before each chunk call
                status = extraction_agent.rate_limit_status()
                rate_display.info(
                    f"📊 Rate limit — "
                    f"RPM: {status['requests_in_window']}/{status['rpm_limit']} "
                    f"({status['rpm_pct']}%)  |  "
                    f"TPM: {status['tokens_in_window']:,}/{status['tpm_limit']:,} "
                    f"({status['tpm_pct']}%)"
                )

                try:
                    extracted = extraction_agent.extract(chunk, schema)
                    data.extend(extracted)
                    st.write(f"   ✅ Chunk {i + 1}/{len(chunks)}: {len(extracted)} items")
                except RuntimeError as e:
                    # Raised after all retries exhausted
                    st.error(f"   ❌ Chunk {i + 1} gave up after retries: {e}")
                except Exception as e:
                    st.warning(f"   ⚠️ Chunk {i + 1} failed: {e}")

            # Use HTML-based pagination (reliable) instead of LLM
            next_page = pagination_agent.find_next_page(html, current_url)

            if not next_page:
                st.write("   ↳ No next page found — stopping.")
                break

            current_url = next_page
            pages_scraped += 1
            time.sleep(1)  # polite delay

        await crawler.close()
        return data

    with st.spinner("Scraping in progress..."):
        # Python 3.10+ safe event loop handling
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        scraped_data = loop.run_until_complete(run())

    # Step 3 — deduplicate
    seen = set()
    unique_data = []
    for item in scraped_data:
        key = str(sorted(item.items()))
        if key not in seen:
            seen.add(key)
            unique_data.append(item)

    st.success(
        f"✅ Extracted **{len(unique_data)}** unique items "
        f"({len(scraped_data) - len(unique_data)} duplicates removed)"
    )

    # Step 4 — preview + export
    if unique_data:
        import pandas as pd
        st.write("### 📊 Preview")
        st.dataframe(pd.DataFrame(unique_data))

    st.write("### 📦 Raw JSON")
    st.json(unique_data)

    json_file = export_json(unique_data)
    csv_file  = export_csv(unique_data)
    st.success(f"💾 Exported → `{json_file}` and `{csv_file}`")
