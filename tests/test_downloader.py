import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scryfall_art_downloader.downloader import download_entries, image_urls, safe_filename
from scryfall_art_downloader.models import DeckEntry


class FakeClient:
    def get_printing(self, set_code, collector_number):
        return {
            "name": "Book of Mazarbul",
            "image_uris": {"png": "https://example.test/card.png"},
        }

    def download(self, url, destination):
        Image.new("RGB", (10, 14), (8, 8, 8)).save(destination, format="PNG")


class DownloaderTests(unittest.TestCase):
    def test_downloads_to_safe_descriptive_filename(self):
        entry = DeckEntry(1, "Book of Mazarbul", "LTR", "116", 1, "source")
        with tempfile.TemporaryDirectory() as directory:
            results = download_entries([entry], Path(directory), client=FakeClient())
            self.assertEqual(results[0].status, "downloaded")
            self.assertTrue(Path(results[0].files[0]).is_file())

    def test_reads_images_from_card_faces(self):
        card = {"card_faces": [{"image_uris": {"art_crop": "front.jpg"}}, {"image_uris": {"art_crop": "back.jpg"}}]}
        self.assertEqual(image_urls(card, "art_crop"), [("front", "front.jpg"), ("back", "back.jpg")])

    def test_sanitizes_windows_filename_characters(self):
        self.assertEqual(safe_filename('A/B: C?'), "A_B_ C_")

    def test_can_process_downloaded_card_with_bleed(self):
        entry = DeckEntry(1, "Book of Mazarbul", "LTR", "116", 1, "source")
        with tempfile.TemporaryDirectory() as directory:
            results = download_entries(
                [entry],
                Path(directory),
                client=FakeClient(),
                add_bleed_edge=True,
            )
            self.assertEqual(len(results[0].processed_files), 1)
            with Image.open(results[0].processed_files[0]) as processed:
                self.assertEqual(processed.size, (822, 1122))

    def test_bleed_rejects_art_crop_mode(self):
        with self.assertRaisesRegex(ValueError, "full-card PNG"):
            download_entries([], Path("unused"), image_type="art_crop", add_bleed_edge=True)


if __name__ == "__main__":
    unittest.main()
