import re
import unicodedata
from collections.abc import Callable, Iterable
from pathlib import Path
from urllib.parse import urlparse

from .client import ScryfallClient, ScryfallError
from .models import DeckEntry, DownloadResult


ProgressCallback = Callable[[int, int, DownloadResult], None]
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_filename(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if not value:
        value = "card"
    if value.upper() in WINDOWS_RESERVED:
        value = f"_{value}"
    return value[:140]


def image_urls(card: dict, image_type: str) -> list[tuple[str, str]]:
    if image_type not in {"png", "art_crop"}:
        raise ValueError("image_type must be 'png' or 'art_crop'")

    if card.get("image_uris", {}).get(image_type):
        return [("", card["image_uris"][image_type])]

    images: list[tuple[str, str]] = []
    faces = card.get("card_faces", [])
    labels = ["front", "back"] if len(faces) == 2 else [f"face-{i + 1}" for i in range(len(faces))]
    for label, face in zip(labels, faces):
        url = face.get("image_uris", {}).get(image_type)
        if url:
            images.append((label, url))
    return images


def download_entries(
    entries: Iterable[DeckEntry],
    output_dir: Path,
    image_type: str = "png",
    overwrite: bool = False,
    client: ScryfallClient | None = None,
    progress: ProgressCallback | None = None,
) -> list[DownloadResult]:
    entries = list(entries)
    output_dir.mkdir(parents=True, exist_ok=True)
    client = client or ScryfallClient()
    results: list[DownloadResult] = []

    for index, entry in enumerate(entries, start=1):
        try:
            card = client.get_printing(entry.set_code, entry.collector_number)
            expected = _normalized_name(entry.name)
            actual = _normalized_name(card.get("name", ""))
            warning = ""
            if expected != actual:
                warning = f"Name mismatch: deck says {entry.name!r}, Scryfall returned {card.get('name')!r}. "

            urls = image_urls(card, image_type)
            if not urls:
                raise ScryfallError(f"No {image_type!r} image is available for this printing")

            files: list[str] = []
            skipped = 0
            base = safe_filename(f"{card['name']} [{entry.set_code} {entry.collector_number}]")
            for face_label, url in urls:
                suffix = ".png" if image_type == "png" else _url_suffix(url)
                face = f"_{face_label}" if face_label else ""
                target = output_dir / f"{base}{face}{suffix}"
                files.append(str(target))
                if target.exists() and not overwrite:
                    skipped += 1
                    continue
                partial = target.with_suffix(target.suffix + ".part")
                try:
                    client.download(url, partial)
                    partial.replace(target)
                finally:
                    partial.unlink(missing_ok=True)

            status = "skipped" if skipped == len(urls) else "downloaded"
            message = warning + ("File already exists." if status == "skipped" else "")
            result = DownloadResult(entry, status, files, message.strip())
        except (ScryfallError, OSError, KeyError, ValueError) as exc:
            result = DownloadResult(entry, "failed", message=str(exc))

        results.append(result)
        if progress:
            progress(index, len(entries), result)

    return results


def _normalized_name(name: str) -> str:
    return " ".join(name.casefold().split())


def _url_suffix(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"

