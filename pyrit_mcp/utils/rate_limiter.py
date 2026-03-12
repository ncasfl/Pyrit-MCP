"""
pyrit_mcp.utils.rate_limiter — Token bucket rate limiter for API requests.

Used by orchestrators to enforce requests-per-second limits when sending
prompts to target applications or LLM backends. This prevents accidental
flooding of targets and manages API quota consumption.
"""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Async token bucket rate limiter.

    Allows up to `rate` tokens per second with a burst capacity of `burst`
    tokens (defaults to `rate`). Each acquire() call consumes one token.

    Example usage in an orchestrator loop::

        limiter = TokenBucketRateLimiter(rate=2.0)  # 2 requests/second
        for prompt in prompts:
            await limiter.acquire()
            response = await send_prompt(prompt)
    """

    def __init__(self, rate: float, burst: float | None = None) -> None:
        """Initialise the token bucket.

        Args:
            rate: Maximum sustained tokens per second.
            burst: Maximum burst capacity. Defaults to ``rate``.
        """
        if rate <= 0:
            raise ValueError(f"Rate must be positive, got {rate}")
        self._rate = rate
        self._burst = burst if burst is not None else rate
        self._tokens = self._burst
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a token is available, then consume it.

        Never raises; always returns once a token is acquired.
        """
        async with self._lock:
            await self._wait_for_token()

    async def _wait_for_token(self) -> None:
        """Refill based on elapsed time and wait if the bucket is empty."""
        while True:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            # Sleep for the exact duration needed to generate one token
            wait_time = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(wait_time)

    @property
    def rate(self) -> float:
        """The configured sustained rate in tokens per second."""
        return self._rate

    @property
    def burst(self) -> float:
        """The configured burst capacity in tokens."""
        return self._burst
