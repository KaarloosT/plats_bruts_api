import time
from pathlib import Path
from typing import Optional

import requests

USER_AGENT = "plats-bruts-api/0.1 (https://github.com/plats-bruts-api; bastanerada77@gmail.com)"


class WikipediaCaFetcher:
    """Fetches Wikipedia pages with on-disk caching and request throttling."""

    def __init__(self, cache_dir: Path, throttle_seconds: float = 1.5):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.throttle_seconds = throttle_seconds
        self._last_request_ts: Optional[float] = None

    def fetch(self, url: str, cache_key: str) -> str:
        cache_file = self.cache_dir / f"{cache_key}.html"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        self._throttle()
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        self._last_request_ts = time.monotonic()

        cache_file.write_text(response.text, encoding="utf-8")
        return response.text

    def _throttle(self) -> None:
        if self._last_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_request_ts
        remaining = self.throttle_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
