from collections import Counter
from enum import Enum
from pathlib import Path

from PIL import Image


CARD_SIZE = (750, 1050)
DEFAULT_BLEED_PIXELS = 36
DARK_TOLERANCE = 0.20
DARK_PERIMETER_THRESHOLD = 0.80


class EdgeTechnique(str, Enum):
    SIMPLE = "simple"
    REPLICATE = "replicate"


def add_bleed(
    source: Path,
    destination: Path,
    bleed_pixels: int = DEFAULT_BLEED_PIXELS,
    card_size: tuple[int, int] = CARD_SIZE,
) -> EdgeTechnique:
    """Resize a card and add print bleed using the original bleed-edgemaxxer algorithm."""
    if bleed_pixels < 1:
        raise ValueError("bleed_pixels must be at least 1")
    if bleed_pixels > min(card_size):
        raise ValueError("bleed_pixels cannot be larger than the card dimensions")

    with Image.open(source) as opened:
        card = opened.convert("RGB")
        if card.size != card_size:
            card = card.resize(card_size, Image.Resampling.LANCZOS)

        perimeter = _perimeter_pixels(card)
        technique, fill_color = _select_technique(perimeter)
        width, height = card.size
        output = Image.new(
            "RGB",
            (width + 2 * bleed_pixels, height + 2 * bleed_pixels),
            fill_color,
        )
        output.paste(card, (bleed_pixels, bleed_pixels))

        if technique is EdgeTechnique.REPLICATE:
            _paste_replicated_edges(output, card, bleed_pixels)

        destination.parent.mkdir(parents=True, exist_ok=True)
        output.save(destination, format="PNG", dpi=(300, 300))
        return technique


def bleed_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}_bleed.png")


def _perimeter_pixels(image: Image.Image) -> list[tuple[int, int, int]]:
    """Match the original app: inspect the top and both side edges."""
    width, height = image.size
    pixels = image.load()
    perimeter = [pixels[x, 0] for x in range(width)]
    perimeter.extend(pixels[0, y] for y in range(1, height - 1))
    perimeter.extend(pixels[width - 1, y] for y in range(1, height - 1))
    return perimeter


def _select_technique(
    perimeter: list[tuple[int, int, int]],
) -> tuple[EdgeTechnique, tuple[int, int, int]]:
    dark_limit = (255 * DARK_TOLERANCE) ** 2 * 3
    dark_count = sum(
        red * red + green * green + blue * blue <= dark_limit
        for red, green, blue in perimeter
    )
    if dark_count / len(perimeter) >= DARK_PERIMETER_THRESHOLD:
        return EdgeTechnique.SIMPLE, Counter(perimeter).most_common(1)[0][0]
    return EdgeTechnique.REPLICATE, (0, 0, 0)


def _paste_replicated_edges(output: Image.Image, card: Image.Image, bleed: int) -> None:
    width, height = card.size
    top = card.crop((0, 0, width, bleed)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    left = card.crop((0, 0, bleed, height)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    right = card.crop((width - bleed, 0, width, height)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    left_corner = left.crop((0, 0, bleed, bleed)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    right_corner = right.crop((0, 0, bleed, bleed)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    output.paste(top, (bleed, 0))
    output.paste(left, (0, bleed))
    output.paste(right, (width + bleed, bleed))
    output.paste(left_corner, (0, 0))
    output.paste(right_corner, (width + bleed, 0))

