import re
from dataclasses import replace

from .models import DeckEntry


CARD_LINE = re.compile(
    r"^\s*(?P<quantity>\d+)[xX]?\s+"
    r"(?P<name>.+?)\s+"
    r"\((?P<set>[A-Za-z0-9]+)\)\s+"
    r"(?P<number>\S+)\s*$"
)
PRISMATIC_MARKER = re.compile(r"\s*\*E\*\s*$", re.IGNORECASE)

IGNORED_HEADINGS = {
    "deck",
    "mainboard",
    "maybeboard",
    "sideboard",
    "commander",
    "companion",
}


class DeckParseError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def parse_deck_list(text: str) -> list[DeckEntry]:
    """Parse Arena-style lines containing an exact set and collector number."""
    entries: list[DeckEntry] = []
    errors: list[str] = []

    for line_number, original in enumerate(text.splitlines(), start=1):
        line = original.strip()
        if not line or line.startswith(("#", "//")):
            continue
        if line.rstrip(":").casefold() in IGNORED_HEADINGS:
            continue
        if line.casefold().startswith("sb:"):
            line = line[3:].strip()
        line = PRISMATIC_MARKER.sub("", line)

        match = CARD_LINE.match(line)
        if not match:
            errors.append(
                f"Line {line_number}: expected '1 Card Name (SET) 123', got {original!r}"
            )
            continue

        name = PRISMATIC_MARKER.sub("", match.group("name")).strip()
        if not name:
            errors.append(f"Line {line_number}: card name is empty")
            continue

        entries.append(
            DeckEntry(
                quantity=int(match.group("quantity")),
                name=name,
                set_code=match.group("set").upper(),
                collector_number=match.group("number"),
                line_number=line_number,
                source_line=original,
            )
        )

    if errors:
        raise DeckParseError(errors)
    if not entries:
        raise DeckParseError(["The deck list does not contain any card lines."])
    return entries


def unique_printings(entries: list[DeckEntry]) -> list[DeckEntry]:
    """Keep the first occurrence of each set/collector-number printing."""
    seen: set[tuple[str, str]] = set()
    unique: list[DeckEntry] = []
    for entry in entries:
        if entry.printing_key not in seen:
            seen.add(entry.printing_key)
            unique.append(entry)
    return unique


def combine_printings(entries: list[DeckEntry]) -> list[DeckEntry]:
    """Combine repeated set/collector-number entries and sum their quantities."""
    positions: dict[tuple[str, str], int] = {}
    combined: list[DeckEntry] = []
    for entry in entries:
        position = positions.get(entry.printing_key)
        if position is None:
            positions[entry.printing_key] = len(combined)
            combined.append(entry)
        else:
            current = combined[position]
            combined[position] = replace(
                current,
                quantity=current.quantity + entry.quantity,
            )
    return combined
