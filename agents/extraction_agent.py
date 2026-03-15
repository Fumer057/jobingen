import json
import re
import logging
import os
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
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
#
# Retries on:  429 RateLimitError, APITimeoutError, APIConnectionError
# Strategy:    exponential backoff (2s → 4s → 8s → 16s → 32s) + random jitter
#              so parallel chunks don't all wake up and hammer the API together
# Max wait:    ~32s per attempt, 3 attempts = up to ~90s total before giving up
#
_RETRY_EXCEPTIONS = (RateLimitError, APITimeoutError, APIConnectionError)

_retry_policy = retry(
    retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
    wait=wait_exponential(multiplier=2, min=2, max=32) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


class ExtractionAgent:

    # gpt-4o-mini tier-1 limits — adjust if you upgrade your OpenAI tier
    RPM_LIMIT = 500
    TPM_LIMIT = 200_000

    def __init__(self):
        self.client  = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30)
        self.limiter = RateLimiter(rpm_limit=self.RPM_LIMIT, tpm_limit=self.TPM_LIMIT)

    # ── Public ────────────────────────────────────────────────────────────────

    def extract(self, page_text: str, schema: dict) -> list:
        """
        Extract structured data from a text chunk.

        Rate limit handling:
          1. RateLimiter proactively sleeps before the call if the rolling
             window is near the RPM or TPM limit.
          2. If a 429 still comes back (e.g. burst from another process),
             tenacity retries with exponential backoff + jitter (up to 3x).
          3. After each successful call the actual token usage is recorded
             so the limiter's estimate stays accurate.
        """
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
                f"Extraction failed after 3 retries (rate limit or timeout). "
                f"Last error: {e.last_attempt.exception()}"
            )

        # Step 3 — record real token usage
        if hasattr(response, "usage") and response.usage:
            self.limiter.record(response.usage.total_tokens)

        # Step 4 — parse and return
        raw           = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "length":
            raw = self._salvage_truncated(raw)

        try:
            result = self._clean_json(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM returned invalid JSON (finish_reason={finish_reason}). "
                f"Error: {e}. Raw (first 300 chars): {raw[:300]}"
            )

        if isinstance(result, dict):
            result = [result]

        if not isinstance(result, list):
            raise ValueError(f"Expected a JSON list, got {type(result).__name__}")

        return result

    def rate_limit_status(self) -> dict:
        """Expose limiter state for the Streamlit UI."""
        return self.limiter.status()

    # ── Private ───────────────────────────────────────────────────────────────

    @_retry_policy
    def _call_api_with_retry(self, prompt: str):
        """Isolated API call so tenacity only wraps the network request."""
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
- Do not invent data
- Return JSON only — no markdown fences, no explanation, no trailing text

Webpage text:
{page_text}
"""

    def _clean_json(self, text: str):
        text = re.sub(r"```json|```", "", text).strip()
        return json.loads(text)

    def _salvage_truncated(self, raw: str) -> str:
        """Recover complete objects from a mid-JSON truncated response."""
        last_complete = raw.rfind("},")
        if last_complete == -1:
            last_complete = raw.rfind("}")
        if last_complete == -1:
            return "[]"
        salvaged      = raw[: last_complete + 1]
        first_bracket = salvaged.find("[")
        if first_bracket == -1:
            return "[]"
        return salvaged[first_bracket:] + "]"
