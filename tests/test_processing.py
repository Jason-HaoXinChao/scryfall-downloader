import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scryfall_art_downloader.processing import (
    EdgeTechnique,
    add_bleed,
    bleed_path,
    millimeters_to_pixels,
)


class BleedProcessingTests(unittest.TestCase):
    def test_dark_card_uses_simple_edge_and_expected_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "card.png"
            destination = bleed_path(source)
            Image.new("RGB", (10, 14), (8, 8, 8)).save(source)

            technique = add_bleed(
                source,
                destination,
                bleed_mm=2,
                card_size_mm=(10, 14),
                dpi=25.4,
            )

            self.assertEqual(technique, EdgeTechnique.SIMPLE)
            with Image.open(destination) as result:
                self.assertEqual(result.size, (14, 18))
                self.assertEqual(result.getpixel((0, 0)), (8, 8, 8))

    def test_bright_card_uses_replicated_edges_on_all_sides(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "card.png"
            destination = bleed_path(source)
            Image.new("RGB", (10, 14), (200, 100, 50)).save(source)

            technique = add_bleed(
                source,
                destination,
                bleed_mm=2,
                card_size_mm=(10, 14),
                dpi=25.4,
            )

            self.assertEqual(technique, EdgeTechnique.REPLICATE)
            with Image.open(destination) as result:
                self.assertEqual(result.getpixel((3, 0)), (200, 100, 50))
                self.assertEqual(result.getpixel((3, 17)), (200, 100, 50))

    def test_transparent_rounded_corners_do_not_create_black_stars(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rounded.png"
            destination = bleed_path(source)
            image = Image.new("RGBA", (10, 14), (180, 120, 60, 255))
            pixels = image.load()
            for point in ((0, 0), (1, 0), (0, 1), (9, 0), (8, 0), (9, 1)):
                pixels[point] = (0, 0, 0, 0)
            image.save(source)

            add_bleed(
                source,
                destination,
                bleed_mm=2,
                card_size_mm=(10, 14),
                dpi=25.4,
            )

            with Image.open(destination) as result:
                self.assertNotEqual(result.getpixel((0, 0)), (0, 0, 0))
                self.assertNotEqual(result.getpixel((13, 0)), (0, 0, 0))

    def test_bleed_extends_outer_pixel_without_repeating_inner_content(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "striped.png"
            destination = bleed_path(source)
            image = Image.new("RGB", (10, 14), (200, 100, 50))
            for x in range(image.width):
                image.putpixel((x, 1), (20, 40, 220))
            image.save(source)

            add_bleed(
                source,
                destination,
                bleed_mm=2,
                card_size_mm=(10, 14),
                dpi=25.4,
            )

            with Image.open(destination) as result:
                self.assertEqual(result.getpixel((4, 0)), (200, 100, 50))
                self.assertNotEqual(result.getpixel((4, 0)), (20, 40, 220))

    def test_default_physical_dimensions_at_300_dpi(self):
        self.assertEqual(millimeters_to_pixels(63), 744)
        self.assertEqual(millimeters_to_pixels(88), 1039)
        self.assertEqual(millimeters_to_pixels(1.5), 18)


if __name__ == "__main__":
    unittest.main()
