import json
import re
import logging
import os
import google.generativeai as genai
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

from utils.rate_limiter import RateLimiter, estimate_tokens

logger = logging.getLogger(__name__)

# ── Retry policy ──────────────────────────────────────────────────────────────
_RETRY_EXCEPTIONS = (RateLimitError, APITimeoutError, APIConnectionError, Exception)

_retry_policy = retry(
    retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
    wait=wait_exponential(multiplier=2, min=2, max=32) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


class ExtractionAgent:

    def __init__(self, provider: str = "openai", api_key: str = None):
        self.provider = provider.lower()
        self.api_key = api_key or (
            os.getenv("GEMINI_API_KEY") if self.provider == "gemini" else 
            os.getenv("ANTHROPIC_API_KEY") if self.provider == "anthropic" else 
            os.getenv("OPENAI_API_KEY")
        )
        
        if self.provider == "gemini":
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.RPM_LIMIT = 15 
            self.TPM_LIMIT = 1_000_000
        elif self.provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.RPM_LIMIT = 50 
            self.TPM_LIMIT = 40_000
        else:
            self.client = OpenAI(api_key=self.api_key, timeout=30)
            self.RPM_LIMIT = 500
            self.TPM_LIMIT = 200_000

        self.limiter = RateLimiter(rpm_limit=self.RPM_LIMIT, tpm_limit=self.TPM_LIMIT)

    # ── Public ────────────────────────────────────────────────────────────────

    def extract(self, page_text: str, schema: dict) -> list:
        schema_str      = json.dumps(schema, indent=2)
        prompt          = self._build_prompt(page_text, schema_str)
        estimated_tokens = estimate_tokens(prompt)

        # Step 1 — proactive throttle
        self.limiter.wait_if_needed(estimated_tokens)

        # Step 2 — call with retry
        try:
            response = self._call_api_with_retry(prompt)
        except RetryError as e:
            raise RuntimeError(
                f"Extraction failed after 3 retries. Last error: {e.last_attempt.exception()}"
            )

        # Step 3 — record usage
        if self.provider == "openai" and hasattr(response, "usage") and response.usage:
            self.limiter.record(response.usage.total_tokens)
        elif self.provider == "anthropic" and hasattr(response, "usage"):
            self.limiter.record(response.usage.input_tokens + response.usage.output_tokens)
        else:
            self.limiter.record(estimated_tokens)

        # Step 4 — parse and return
        if self.provider == "gemini":
            raw = response.text
            finish_reason = "stop"
        elif self.provider == "anthropic":
            raw = response.content[0].text
            finish_reason = "stop" if response.stop_reason == "end_turn" else "length"
        else:
            raw = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

        if finish_reason == "length":
            raw = self._salvage_truncated(raw)

        try:
            result = self._clean_json(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM returned invalid JSON. Error: {e}. Raw (first 300 chars): {raw[:300]}"
            )

        if isinstance(result, dict):
            for val in result.values():
                if isinstance(val, list):
                    return val
            result = [result]

        return result

    def rate_limit_status(self) -> dict:
        return self.limiter.status()

    # ── Private ───────────────────────────────────────────────────────────────

    @_retry_policy
    def _call_api_with_retry(self, prompt: str):
        if self.provider == "gemini":
            return self.model.generate_content(prompt)
        elif self.provider == "anthropic":
            return self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2000,
                temperature=0,
                system="Return ONLY valid JSON. No explanation.",
                messages=[{"role": "user", "content": prompt}]
            )
        else:
            return self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=2000,
            )

    def _build_prompt(self, page_text: str, schema_str: str) -> str:
        return f"""
Extract structured data from the webpage text below.
Required schema:
{schema_str}

Rules:
- Return a JSON array of objects matching the schema exactly
- If a field is missing or unknown, set it to null
- Return JSON only — no markdown fences, no explanation
Webpage text:
{page_text}
"""

    def _clean_json(self, text: str):
        text = re.sub(r"```json|```", "", text).strip()
        return json.loads(text)

    def _salvage_truncated(self, raw: str) -> str:
        last_complete = raw.rfind("},")
        if last_complete == -1: last_complete = raw.rfind("}")
        if last_complete == -1: return "[]"
        salvaged = raw[: last_complete + 1]
        first_bracket = salvaged.find("[")
        if first_bracket == -1: return "[]"
        return salvaged[first_bracket:] + "]"
