import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scryfall_art_downloader.processing import EdgeTechnique, add_bleed, bleed_path


class BleedProcessingTests(unittest.TestCase):
    def test_dark_card_uses_simple_edge_and_expected_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "card.png"
            destination = bleed_path(source)
            Image.new("RGB", (10, 14), (8, 8, 8)).save(source)

            technique = add_bleed(source, destination, bleed_pixels=2, card_size=(10, 14))

            self.assertEqual(technique, EdgeTechnique.SIMPLE)
            with Image.open(destination) as result:
                self.assertEqual(result.size, (14, 18))
                self.assertEqual(result.getpixel((0, 0)), (8, 8, 8))

    def test_bright_card_uses_replicated_edges_and_black_bottom(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "card.png"
            destination = bleed_path(source)
            Image.new("RGB", (10, 14), (200, 100, 50)).save(source)

            technique = add_bleed(source, destination, bleed_pixels=2, card_size=(10, 14))

            self.assertEqual(technique, EdgeTechnique.REPLICATE)
            with Image.open(destination) as result:
                self.assertEqual(result.getpixel((3, 0)), (200, 100, 50))
                self.assertEqual(result.getpixel((3, 17)), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
