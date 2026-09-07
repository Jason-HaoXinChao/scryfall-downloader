import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scryfall_art_downloader.downloader import download_entries, image_urls, safe_filename
from scryfall_art_downloader.models import DeckEntry


class FakeClient:
    def __init__(self):
        self.download_count = 0

    def get_printing(self, set_code, collector_number, card_name=None):
        return {
            "name": "Book of Mazarbul",
            "image_uris": {"png": "https://example.test/card.png"},
        }

    def download(self, url, destination):
        self.download_count += 1
        Image.new("RGB", (10, 14), (8, 8, 8)).save(destination, format="PNG")


class FakeDoubleSidedClient(FakeClient):
    def get_printing(self, set_code, collector_number, card_name=None):
        return {
            "name": "Delver of Secrets // Insectile Aberration",
            "card_faces": [
                {
                    "name": "Delver of Secrets",
                    "image_uris": {"png": "https://example.test/front.png"},
                },
                {
                    "name": "Insectile Aberration",
                    "image_uris": {"png": "https://example.test/back.png"},
                },
            ],
        }


class FakeAlternateNameClient(FakeClient):
    def get_printing(self, set_code, collector_number, card_name=None):
        return {
            "name": "Queen Marchesa",
            "flavor_name": "Amunet, Tyrants' End",
            "image_uris": {"png": "https://example.test/amunet.png"},
        }


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
                self.assertEqual(processed.size, (780, 1075))

    def test_bleed_rejects_art_crop_mode(self):
        with self.assertRaisesRegex(ValueError, "full-card PNG"):
            download_entries([], Path("unused"), image_type="art_crop", add_bleed_edge=True)

    def test_quantity_creates_numbered_local_copies(self):
        entry = DeckEntry(3, "Book of Mazarbul", "LTR", "116", 1, "source")
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            results = download_entries([entry], Path(directory), client=client)
            names = [Path(filename).name for filename in results[0].files]
            self.assertEqual(len(names), 3)
            self.assertTrue(names[0].endswith("_copy-1.png"))
            self.assertTrue(names[1].endswith("_copy-2.png"))
            self.assertTrue(names[2].endswith("_copy-3.png"))
            self.assertTrue(all(Path(filename).is_file() for filename in results[0].files))
            self.assertEqual(client.download_count, 1)

    def test_double_sided_card_downloads_both_faces_for_each_copy(self):
        entry = DeckEntry(2, "Delver of Secrets", "MID", "47", 1, "source")
        client = FakeDoubleSidedClient()
        with tempfile.TemporaryDirectory() as directory:
            results = download_entries([entry], Path(directory), client=client)
            names = [Path(filename).name for filename in results[0].files]

            self.assertEqual(len(names), 4)
            self.assertTrue(any(name.endswith("_front_copy-1.png") for name in names))
            self.assertTrue(any(name.endswith("_front_copy-2.png") for name in names))
            self.assertTrue(any(name.endswith("_back_copy-1.png") for name in names))
            self.assertTrue(any(name.endswith("_back_copy-2.png") for name in names))
            self.assertEqual(client.download_count, 2)
            self.assertNotIn("Name mismatch", results[0].message)

    def test_double_sided_card_processes_both_faces_with_bleed(self):
        entry = DeckEntry(1, "Delver of Secrets", "MID", "47", 1, "source")
        with tempfile.TemporaryDirectory() as directory:
            results = download_entries(
                [entry],
                Path(directory),
                client=FakeDoubleSidedClient(),
                add_bleed_edge=True,
            )

            self.assertEqual(len(results[0].processed_files), 2)
            self.assertTrue(all(Path(filename).is_file() for filename in results[0].processed_files))
            self.assertTrue(all(filename.endswith("_bleed.png") for filename in results[0].processed_files))

    def test_alternate_name_print_uses_its_flavor_name_in_filename(self):
        entry = DeckEntry(1, "Amunet, Tyrants' End", "SLD", None, 1, "source")
        with tempfile.TemporaryDirectory() as directory:
            result = download_entries(
                [entry],
                Path(directory),
                client=FakeAlternateNameClient(),
            )[0]

            self.assertEqual(result.status, "downloaded")
            self.assertIn("Amunet, Tyrants' End [SLD]", Path(result.files[0]).name)
            self.assertNotIn("Name mismatch", result.message)


if __name__ == "__main__":
    unittest.main()
