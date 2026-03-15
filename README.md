# 🕷️ Universal AI Web Scraper (Jobingen)

A powerful, "brain-first" web scraper that uses Large Language Models (LLMs) to extract structured data from any website without requiring CSS selectors or XPaths.

## 🚀 Key Features

- **Semantic Extraction**: Describe the data you want in plain English (e.g., "Extract job titles and salaries").
- **Universal Compatibility**: Works on any site—from job boards to e-commerce and research databases.
- **Multi-LLM Support**: Supports both **Google Gemini 2.0 Flash** and **OpenAI GPT-4o-mini**.
- **Ultra-Low Credit Mode**: 
  - **Manual Schema**: Skip AI schema generation to save tokens.
  - **Aggressive Cleaning**: Strips HTML noise (ads, nav, footers) to minimize input costs.
  - **Top-Down Extraction**: Focuses on the most relevant content to stay within free-tier limits.
- **Dynamic Pydantic Models**: Generates data validation models on-the-fly based on your extraction requirements.
- **Export Options**: Download your data instantly as **CSV** or **JSON**.

## 🛠️ Technology Stack

| Component | Technology |
| :--- | :--- |
| **Frontend** | Streamlit |
| **Crawler** | Playwright (Stealth mode) |
| **HTML Parsing** | BeautifulSoup4 |
| **Logic/Models** | Python, Pydantic, Instructor |
| **AI Intelligence** | Gemini 2.0, GPT-4o-mini |

## 🏗️ Technical Architecture

1. **Smart Crawling**: The app launches a headless browser, renders JavaScript, and captures the absolute text content.
2. **Noise Reduction**: Custom filters remove non-essential HTML tags (scripts, styles, ads) reducing token waste by up to 80%.
3. **Schema Mapping**: If dynamic mode is used, an AI agent converts your natural language prompt into a structured JSON schema.
4. **LLM Extraction**: The cleaned content and schema are sent to the LLM, which identifies and formats the relevant data into a validated JSON list.

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
   Create a `.env` file or enter keys directly in the UI.
   ```env
   GEMINI_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   ```

4. **Run the App**:
   ```bash
   streamlit run app.py
   ```

## 💸 Cost Optimization Tips

- **Enable Manual Schema**: If you know the fields you want (e.g., `{"price": "string"}`), provide them manually to save one full AI call.
- **Disable Pagination**: Only enable pagination if you strictly need results from multiple pages.
- **Use GPT-4o-mini**: This model is extremely efficient and cheaper for high-volume extractions.

---
Developed as part of the **Jobingen** project.
