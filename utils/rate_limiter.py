"""
utils/rate_limiter.py

Proactive rate limiter for OpenAI API calls.

gpt-4o-mini limits (free/tier-1):
  - 500  requests per minute  (RPM)
  - 200,000 tokens per minute (TPM)

This class tracks both in a rolling 60-second window and sleeps
BEFORE a call would breach the limit, rather than waiting for a 429
error to come back.

Usage:
    limiter = RateLimiter(rpm_limit=500, tpm_limit=200_000)

    # Before each API call:
    limiter.wait_if_needed(estimated_tokens=1500)

    # After each API call (pass actual token usage from the response):
    limiter.record(tokens_used=response.usage.total_tokens)
"""

import time
import threading
from collections import deque


class RateLimiter:

    def __init__(
        self,
        rpm_limit: int = 500,
        tpm_limit: int = 200_000,
        window_seconds: int = 60,
    ):
        self.rpm_limit      = rpm_limit
        self.tpm_limit      = tpm_limit
        self.window         = window_seconds

        # Thread-safe deques of (timestamp, tokens) tuples
        self._lock          = threading.Lock()
        self._requests      = deque()   # (timestamp,)
        self._tokens        = deque()   # (timestamp, token_count)

    # ── Public API ────────────────────────────────────────────────────────────

    def wait_if_needed(self, estimated_tokens: int = 1000) -> None:
        """
        Block until making a call with `estimated_tokens` would be safe.
        Call this BEFORE every API request.
        """
        while True:
            with self._lock:
                self._purge_old()

                rpm_ok = len(self._requests) + 1 <= self.rpm_limit
                tpm_ok = self._token_sum() + estimated_tokens <= self.tpm_limit

                if rpm_ok and tpm_ok:
                    # Reserve the slot now so concurrent callers don't race
                    now = time.monotonic()
                    self._requests.append(now)
                    self._tokens.append((now, estimated_tokens))
                    return

                # Calculate how long until the oldest entry expires
                sleep_for = self._sleep_duration()

            # Sleep outside the lock so other threads aren't blocked
            time.sleep(sleep_for)

    def record(self, tokens_used: int) -> None:
        """
        Update the actual token count after a call completes.
        Corrects the estimate we pre-recorded in wait_if_needed().
        """
        with self._lock:
            self._purge_old()
            # Replace the most recent estimate with the real value
            if self._tokens:
                ts, _ = self._tokens[-1]
                self._tokens[-1] = (ts, tokens_used)

    def status(self) -> dict:
        """Returns current usage snapshot — useful for UI display."""
        with self._lock:
            self._purge_old()
            return {
                "requests_in_window": len(self._requests),
                "tokens_in_window":   self._token_sum(),
                "rpm_limit":          self.rpm_limit,
                "tpm_limit":          self.tpm_limit,
                "rpm_pct":            round(len(self._requests) / self.rpm_limit * 100, 1),
                "tpm_pct":            round(self._token_sum()   / self.tpm_limit  * 100, 1),
            }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _purge_old(self) -> None:
        """Remove entries older than the rolling window. Must be called under lock."""
        cutoff = time.monotonic() - self.window
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        while self._tokens and self._tokens[0][0] < cutoff:
            self._tokens.popleft()

    def _token_sum(self) -> int:
        return sum(t for _, t in self._tokens)

    def _sleep_duration(self) -> float:
        """
        How long to wait until the oldest tracked entry exits the window.
        Adds a 50ms buffer to avoid edge-case races.
        """
        now = time.monotonic()
        oldest_req   = self._requests[0]  if self._requests else now
        oldest_tok   = self._tokens[0][0] if self._tokens    else now
        oldest       = min(oldest_req, oldest_tok)
        return max(0.0, (oldest + self.window - now) + 0.05)


def estimate_tokens(text: str) -> int:
    """
    Rough token estimate without importing tiktoken.
    Rule of thumb: 1 token ≈ 4 characters for English text.
    We add 20% headroom for prompt overhead.
    """
    return int(len(text) / 4 * 1.2)
