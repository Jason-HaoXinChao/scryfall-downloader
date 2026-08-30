from collections import Counter
from enum import Enum
from pathlib import Path

from PIL import Image, ImageOps


DEFAULT_DPI = 300
CARD_SIZE_MM = (63.0, 88.0)
DEFAULT_BLEED_MM = 1.5
DARK_TOLERANCE = 0.20
DARK_PERIMETER_THRESHOLD = 0.80


class EdgeTechnique(str, Enum):
    SIMPLE = "simple"
    REPLICATE = "replicate"


def add_bleed(
    source: Path,
    destination: Path,
    bleed_mm: float = DEFAULT_BLEED_MM,
    card_size_mm: tuple[float, float] = CARD_SIZE_MM,
    dpi: int = DEFAULT_DPI,
) -> EdgeTechnique:
    """Create an exact physical trim size plus bleed without stretching the card."""
    if bleed_mm <= 0:
        raise ValueError("bleed_mm must be greater than zero")
    if dpi <= 0:
        raise ValueError("dpi must be greater than zero")
    if bleed_mm > min(card_size_mm):
        raise ValueError("bleed_mm cannot be larger than the card dimensions")

    card_size = tuple(millimeters_to_pixels(value, dpi) for value in card_size_mm)
    bleed_pixels = millimeters_to_pixels(bleed_mm, dpi)

    with Image.open(source) as opened:
        rgba = opened.convert("RGBA")
        if rgba.size != card_size:
            rgba = ImageOps.fit(
                rgba,
                card_size,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
        underlay = _inset_underlay(rgba, bleed_pixels)
        card = Image.alpha_composite(underlay.convert("RGBA"), rgba).convert("RGB")
        perimeter = _perimeter_pixels(card)
        technique, fill_color = _select_technique(perimeter)
        width, height = card.size
        output_size = (width + 2 * bleed_pixels, height + 2 * bleed_pixels)
        if technique is EdgeTechnique.SIMPLE:
            output = Image.new("RGB", output_size, fill_color)
        else:
            output = Image.new("RGB", output_size, (0, 0, 0))
            output.paste(card, (bleed_pixels, bleed_pixels))
            _paste_extended_edges(output, card, bleed_pixels)

        output.paste(card, (bleed_pixels, bleed_pixels))

        destination.parent.mkdir(parents=True, exist_ok=True)
        output.save(destination, format="PNG", dpi=(dpi, dpi))
        return technique


def bleed_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}_bleed.png")


def millimeters_to_pixels(millimeters: float, dpi: int = DEFAULT_DPI) -> int:
    return round(millimeters * dpi / 25.4)


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


def _paste_extended_edges(output: Image.Image, card: Image.Image, bleed: int) -> None:
    """Extend the outermost pixels without repeating visible card features."""
    width, height = card.size
    top = card.crop((0, 0, width, 1)).resize((width, bleed))
    bottom = card.crop((0, height - 1, width, height)).resize((width, bleed))
    left = card.crop((0, 0, 1, height)).resize((bleed, height))
    right = card.crop((width - 1, 0, width, height)).resize((bleed, height))

    output.paste(top, (bleed, 0))
    output.paste(bottom, (bleed, height + bleed))
    output.paste(left, (0, bleed))
    output.paste(right, (width + bleed, bleed))
    output.paste(card.getpixel((0, 0)), (0, 0, bleed, bleed))
    output.paste(card.getpixel((width - 1, 0)), (width + bleed, 0, width + 2 * bleed, bleed))
    output.paste(card.getpixel((0, height - 1)), (0, height + bleed, bleed, height + 2 * bleed))
    output.paste(
        card.getpixel((width - 1, height - 1)),
        (width + bleed, height + bleed, width + 2 * bleed, height + 2 * bleed),
    )


def _inset_underlay(rgba: Image.Image, inset: int) -> Image.Image:
    """Build an opaque background from inside the rounded card boundary."""
    width, height = rgba.size
    inner = rgba.crop((inset, inset, width - inset, height - inset)).convert("RGB")
    return inner.resize((width, height), Image.Resampling.LANCZOS)
