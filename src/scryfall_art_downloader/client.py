import json
import time
import unicodedata
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://api.scryfall.com"
USER_AGENT = "scryfall-card-art-downloader/0.3.0 (personal desktop application)"
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

    def get_printing(
        self,
        set_code: str | None,
        collector_number: str | None,
        card_name: str | None = None,
    ) -> dict[str, Any]:
        url = printing_url(set_code, collector_number, card_name)
        card = self._get_json(url)
        if collector_number or not card_name or card_has_name(card, card_name):
            return card

        prints_url = card.get("prints_search_uri")
        while prints_url:
            page = self._get_json(prints_url)
            for candidate in page.get("data", []):
                if set_code and candidate.get("set", "").casefold() != set_code.casefold():
                    continue
                if card_has_name(candidate, card_name):
                    return candidate
            prints_url = page.get("next_page") if page.get("has_more") else None

        set_label = f" in {set_code}" if set_code else ""
        raise ScryfallError(
            f"Scryfall found the rules card {card.get('name')!r}, but no printing named "
            f"{card_name!r}{set_label}"
        )

    def _get_json(self, url: str) -> dict[str, Any]:
        self._respect_rate_limit()
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
                f"Scryfall returned HTTP {exc.code}: {detail}"
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


def printing_url(
    set_code: str | None,
    collector_number: str | None,
    card_name: str | None = None,
) -> str:
    """Build an exact printing URL, falling back to exact name within a set."""
    if collector_number and not set_code:
        raise ValueError("set_code is required when collector_number is supplied")
    if collector_number:
        return (
            f"{API_ROOT}/cards/{quote(set_code.lower(), safe='')}"
            f"/{quote(collector_number, safe='')}"
        )
    if not card_name:
        raise ValueError("card_name is required when collector_number is omitted")
    parameters = {"exact": card_name}
    if set_code:
        parameters["set"] = set_code.lower()
    query = urlencode(parameters)
    return f"{API_ROOT}/cards/named?{query}"


def card_has_name(card: dict[str, Any], expected_name: str) -> bool:
    expected = normalize_name(expected_name)
    return expected in {normalize_name(name) for name in card_names(card)}


def card_names(card: dict[str, Any]) -> list[str]:
    """Return rules, localized, and alternate flavor names for a printing."""
    names = [
        card.get("name"),
        card.get("printed_name"),
        card.get("flavor_name"),
    ]
    for face in card.get("card_faces", []):
        names.extend(
            (face.get("name"), face.get("printed_name"), face.get("flavor_name"))
        )
    return [name for name in names if name]


def normalize_name(name: str) -> str:
    punctuation = str.maketrans(
        {
            "\u2018": "'",
            "\u2019": "'",
            "\u02bc": "'",
            "\u2010": "-",
            "\u2011": "-",
            "\u2013": "-",
            "\u2014": "-",
        }
    )
    normalized = unicodedata.normalize("NFKC", name).translate(punctuation)
    return " ".join(normalized.casefold().split())
