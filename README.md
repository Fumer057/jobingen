# 🕷️ Universal AI Web Scraper (Jobingen)

A powerful, modular web scraper that uses Large Language Models (LLMs) to extract structured data from any website. No CSS selectors or XPaths required.

## 🚀 Key Features

- **Multi-LLM Support**: Choose between **Google Gemini 2.0**, **OpenAI GPT-4o-mini**, and **Anthropic Claude 3.5**.
- **Proactive Rate Limiting**: Built-in `RateLimiter` tracks RPM/TPM and proactively sleeps to stay within API tier limits (prevents 429 errors).
- **Smart Text Chunking**: Uses `langchain-text-splitters` to handle large pages by splitting them into overlapping context-aware chunks.
- **Robust Retries**: Native support for exponential backoff and jitter using `tenacity` for reliable network calls.
- **Privacy First**: Sensitive API keys loaded from `.env` are masked and hidden in the UI.
- **Automatic Pagination**: Heuristic-based discovery of "Next" page links.
- **Dynamic Pydantic Models**: Generates data validation models on-the-fly.

## 🏗️ Modular Architecture

The project follows a clean, class-based design:
- `WebCrawler`: Manages Playwright browser lifecycle and content fetching.
- `ExtractionAgent`: Cross-provider extraction logic with rate limiting and retry handling.
- `SchemaAgent`: Converts natural language prompts into technical JSON schemas.
- `PaginationAgent`: Heuristic link discovery for multi-page scraping.
- `RateLimiter`: Thread-safe rolling window limiter for API safety.

## 🛠️ Technology Stack

| Component | Technology |
| :--- | :--- |
| **Frontend** | Streamlit |
| **Crawler** | Playwright |
| **Parsing** | BeautifulSoup4 |
| **Chunking** | LangChain Text Splitters |
| **AI Providers** | Google Gemini, OpenAI, Anthropic |

## 📦 Setup & Installation

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/Fumer057/jobingen.git
   cd jobingen
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Configure API Keys**:
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_key
   OPENAI_API_KEY=your_key
   ANTHROPIC_API_KEY=your_key
   ```

4. **Run the App**:
   ```bash
   streamlit run app.py
   ```

---
Developed as part of the **Jobingen** project.
