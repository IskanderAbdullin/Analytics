"""Small HTTP transport with caching, throttling, and retry handling."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MarketDataApiError(RuntimeError):
    """Sanitised provider API error; never includes request headers or credentials."""

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.status_code = status_code


class HttpTransport:
    """Provider-neutral HTTP transport. Cache keys never contain authorization headers."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        cache_dir: str | Path,
        default_headers: dict[str, str] | None = None,
        cache_namespace: str | None = None,
        min_interval_seconds: float = 0.0,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        opener: Callable[..., Any] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must not be negative")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_headers = dict(default_headers or {})
        self.cache_namespace = cache_namespace
        self.min_interval_seconds = min_interval_seconds
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._opener = opener or urlopen
        self._sleep = sleeper
        self._monotonic = monotonic
        self._last_request_at: float | None = None

    def set_header(self, name: str, value: str) -> None:
        self.default_headers[name] = value

    def _throttle(self) -> None:
        if self._last_request_at is not None:
            elapsed = self._monotonic() - self._last_request_at
            wait_for = self.min_interval_seconds - elapsed
            if wait_for > 0:
                self._sleep(wait_for)
        self._last_request_at = self._monotonic()

    def _cache_path(
        self,
        method: str,
        url: str,
        body: bytes | None,
        response_kind: str,
    ) -> Path:
        digest = hashlib.sha256()
        scope = self.cache_namespace or self.default_headers.get("Authorization", "")
        digest.update(scope.encode("utf-8"))
        digest.update(b"\n")
        digest.update(method.encode("ascii"))
        digest.update(b"\n")
        digest.update(url.encode("utf-8"))
        digest.update(b"\n")
        digest.update(body or b"")
        return self.cache_dir / f"{digest.hexdigest()}.{response_kind}"

    @staticmethod
    def _retry_delay(value: str | None, attempt: int) -> float:
        if value:
            try:
                return max(0.0, min(float(value), 60.0))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    return max(0.0, min(retry_at.timestamp() - time.time(), 60.0))
                except (TypeError, ValueError, OverflowError):
                    pass
        return float(min(2**attempt, 30))

    def request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache: bool = True,
        refresh: bool = False,
        response_kind: str = "bin",
    ) -> bytes:
        method = method.upper()
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            query = urlencode(
                [
                    (
                        key,
                        str(value).lower() if isinstance(value, bool) else str(value),
                    )
                    for key, value in params.items()
                    if value is not None
                ]
            )
            if query:
                url = f"{url}?{query}"

        body = (
            json.dumps(json_body, separators=(",", ":"), sort_keys=True).encode("utf-8")
            if json_body is not None
            else None
        )
        cache_path = self._cache_path(method, url, body, response_kind)
        if cache and not refresh and cache_path.exists():
            return cache_path.read_bytes()

        request_headers = {"Accept": "*/*", **self.default_headers, **(headers or {})}
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        request = Request(url, data=body, headers=request_headers, method=method)

        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    payload = response.read()
                if cache:
                    cache_path.write_bytes(payload)
                return payload
            except HTTPError as error:
                retryable = error.code == 429 or 500 <= error.code <= 599
                if retryable and attempt < self.max_retries:
                    self._sleep(self._retry_delay(error.headers.get("Retry-After"), attempt))
                    continue
                raise MarketDataApiError(
                    self.provider,
                    f"HTTP {error.code} for {method} {path}",
                    status_code=error.code,
                ) from None
            except URLError as error:
                if attempt < self.max_retries:
                    self._sleep(float(min(2**attempt, 30)))
                    continue
                reason = getattr(error, "reason", "network error")
                raise MarketDataApiError(
                    self.provider,
                    f"network request failed for {method} {path}: {reason}",
                ) from None
            except TimeoutError:
                if attempt < self.max_retries:
                    self._sleep(float(min(2**attempt, 30)))
                    continue
                raise MarketDataApiError(
                    self.provider,
                    f"request timed out for {method} {path}",
                ) from None

        raise MarketDataApiError(self.provider, f"request failed for {method} {path}")

    def request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        payload = self.request_bytes(
            method, path, response_kind="json", **kwargs
        )
        try:
            result = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MarketDataApiError(
                self.provider, f"invalid JSON response for {method} {path}"
            ) from error
        if not isinstance(result, dict):
            raise MarketDataApiError(
                self.provider, f"unexpected JSON response shape for {method} {path}"
            )
        return result
