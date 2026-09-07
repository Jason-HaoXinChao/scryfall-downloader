import re
import shutil
import unicodedata
from collections.abc import Callable, Iterable
from pathlib import Path
from urllib.parse import urlparse

from .client import ScryfallClient, ScryfallError, card_has_name
from .models import DeckEntry, DownloadResult
from .processing import DEFAULT_BLEED_MM, add_bleed, bleed_path


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
    add_bleed_edge: bool = False,
    bleed_mm: float = DEFAULT_BLEED_MM,
    client: ScryfallClient | None = None,
    progress: ProgressCallback | None = None,
) -> list[DownloadResult]:
    if add_bleed_edge and image_type != "png":
        raise ValueError("Bleed processing requires full-card PNG images")
    entries = list(entries)
    output_dir.mkdir(parents=True, exist_ok=True)
    client = client or ScryfallClient()
    results: list[DownloadResult] = []

    for index, entry in enumerate(entries, start=1):
        try:
            card = client.get_printing(
                entry.set_code,
                entry.collector_number,
                entry.name,
            )
            warning = ""
            if not card_has_name(card, entry.name):
                warning = f"Name mismatch: deck says {entry.name!r}, Scryfall returned {card.get('name')!r}. "

            urls = image_urls(card, image_type)
            if not urls:
                raise ScryfallError(f"No {image_type!r} image is available for this printing")

            files: list[str] = []
            processed_files: list[str] = []
            skipped = 0
            changed = False
            printing_label = entry.set_code or ""
            if entry.collector_number:
                printing_label += f" {entry.collector_number}"
            printing_suffix = f" [{printing_label}]" if printing_label else ""
            display_name = card.get("flavor_name") or card.get("printed_name") or card["name"]
            base = safe_filename(f"{display_name}{printing_suffix}")
            for face_label, url in urls:
                suffix = ".png" if image_type == "png" else _url_suffix(url)
                face = f"_{face_label}" if face_label else ""
                targets = [
                    output_dir / f"{base}{face}{_copy_label(copy, entry.quantity)}{suffix}"
                    for copy in range(1, entry.quantity + 1)
                ]
                files.extend(str(target) for target in targets)
                missing = [target for target in targets if overwrite or not target.exists()]
                skipped += len(targets) - len(missing)
                if missing:
                    seed = missing[0]
                    partial = seed.with_suffix(seed.suffix + ".part")
                    try:
                        client.download(url, partial)
                        partial.replace(seed)
                        changed = True
                    finally:
                        partial.unlink(missing_ok=True)
                    for target in missing[1:]:
                        partial = target.with_suffix(target.suffix + ".part")
                        try:
                            shutil.copyfile(seed, partial)
                            partial.replace(target)
                        finally:
                            partial.unlink(missing_ok=True)

            if add_bleed_edge:
                for filename in files:
                    source = Path(filename)
                    processed = bleed_path(source)
                    processed_files.append(str(processed))
                    if processed.exists() and not overwrite:
                        continue
                    add_bleed(source, processed, bleed_mm=bleed_mm)
                    changed = True

            status = "downloaded" if changed else "skipped"
            message = warning + ("All output files already exist." if status == "skipped" else "")
            result = DownloadResult(
                entry,
                status,
                files,
                processed_files,
                message.strip(),
            )
        except (ScryfallError, OSError, KeyError, ValueError) as exc:
            result = DownloadResult(entry, "failed", message=str(exc))

        results.append(result)
        if progress:
            progress(index, len(entries), result)

    return results


def _url_suffix(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def _copy_label(copy_number: int, quantity: int) -> str:
    return f"_copy-{copy_number}" if quantity > 1 else ""
