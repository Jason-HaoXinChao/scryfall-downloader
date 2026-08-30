import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


API_ROOT = "https://api.scryfall.com"
USER_AGENT = "scryfall-card-art-downloader/0.2.0 (personal desktop application)"
ACCEPT = "application/json;q=0.9,*/*;q=0.8"


class ScryfallError(RuntimeError):
    pass


class ScryfallClient:
    def __init__(self, delay: float = 0.15, timeout: float = 30.0):
        if delay < 0.1:
            raise ValueError("Scryfall API delay must be at least 0.1 seconds")
        self.delay = delay
        self.timeout = timeout
        self._last_api_request = 0.0

    def get_printing(self, set_code: str, collector_number: str) -> dict[str, Any]:
        self._respect_rate_limit()
        url = (
            f"{API_ROOT}/cards/{quote(set_code.lower(), safe='')}"
            f"/{quote(collector_number, safe='')}"
        )
        request = Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": ACCEPT},
        )
        self._last_api_request = time.monotonic()
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            detail = self._error_detail(exc)
            raise ScryfallError(
                f"Scryfall returned HTTP {exc.code} for {set_code} {collector_number}: {detail}"
            ) from exc
        except URLError as exc:
            raise ScryfallError(f"Could not reach Scryfall: {exc.reason}") from exc

    def download(self, url: str, destination) -> None:
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"})
        try:
            with urlopen(request, timeout=self.timeout) as response, destination.open("wb") as output:
                while chunk := response.read(1024 * 128):
                    output.write(chunk)
        except (HTTPError, URLError, OSError) as exc:
            raise ScryfallError(f"Image download failed: {exc}") from exc

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_api_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    @staticmethod
    def _error_detail(exc: HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            return payload.get("details", exc.reason)
        except (ValueError, UnicodeDecodeError, OSError):
            return str(exc.reason)
