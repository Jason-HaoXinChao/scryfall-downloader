import unittest

from scryfall_art_downloader.client import ScryfallClient, card_has_name, printing_url


class StubScryfallClient(ScryfallClient):
    def __init__(self, responses):
        super().__init__()
        self.responses = responses
        self.requested_urls = []

    def _get_json(self, url):
        self.requested_urls.append(url)
        return self.responses[url]


class PrintingUrlTests(unittest.TestCase):
    def test_uses_collector_endpoint_when_number_is_present(self):
        self.assertEqual(
            printing_url("MH1", "7"),
            "https://api.scryfall.com/cards/mh1/7",
        )

    def test_uses_exact_name_constrained_to_set_without_number(self):
        self.assertEqual(
            printing_url("MH1", None, "Ephemerate"),
            "https://api.scryfall.com/cards/named?exact=Ephemerate&set=mh1",
        )

    def test_encodes_special_characters_in_name(self):
        url = printing_url("MH2", None, "Fire // Ice")
        self.assertIn("exact=Fire+%2F%2F+Ice", url)

    def test_uses_unconstrained_exact_name_without_set(self):
        self.assertEqual(
            printing_url(None, None, "Ephemerate"),
            "https://api.scryfall.com/cards/named?exact=Ephemerate",
        )

    def test_rejects_collector_number_without_set(self):
        with self.assertRaisesRegex(ValueError, "set_code"):
            printing_url(None, "7", "Ephemerate")


class AlternateNameTests(unittest.TestCase):
    def test_recognizes_rules_printed_flavor_and_face_names(self):
        card = {
            "name": "Queen Marchesa",
            "printed_name": "Printed Queen",
            "flavor_name": "Amunet, Tyrants' End",
            "card_faces": [{"name": "Front Face"}, {"flavor_name": "Back Alias"}],
        }
        for name in (
            "Queen Marchesa",
            "Printed Queen",
            "Amunet, Tyrants' End",
            "Front Face",
            "Back Alias",
        ):
            self.assertTrue(card_has_name(card, name))
        self.assertTrue(card_has_name(card, "Amunet, Tyrants’ End"))

    def test_selects_matching_flavor_name_from_all_printings(self):
        named_url = printing_url(None, None, "Amunet, Tyrants' End")
        original = {
            "name": "Queen Marchesa",
            "set": "CN2",
            "prints_search_uri": "https://example.test/prints",
        }
        alternate = {
            "name": "Queen Marchesa",
            "flavor_name": "Amunet, Tyrants' End",
            "set": "SLD",
            "collector_number": "1559",
        }
        client = StubScryfallClient(
            {
                named_url: original,
                "https://example.test/prints": {
                    "data": [original, alternate],
                    "has_more": False,
                },
            }
        )

        result = client.get_printing(None, None, "Amunet, Tyrants' End")

        self.assertIs(result, alternate)
        self.assertEqual(len(client.requested_urls), 2)

    def test_alternate_name_selection_respects_requested_set(self):
        named_url = printing_url("SLD", None, "Amunet, Tyrants' End")
        original = {
            "name": "Queen Marchesa",
            "set": "CN2",
            "prints_search_uri": "https://example.test/prints",
        }
        wrong_set = {
            "name": "Queen Marchesa",
            "flavor_name": "Amunet, Tyrants' End",
            "set": "ABC",
        }
        correct_set = {
            "name": "Queen Marchesa",
            "flavor_name": "Amunet, Tyrants' End",
            "set": "SLD",
        }
        client = StubScryfallClient(
            {
                named_url: original,
                "https://example.test/prints": {
                    "data": [wrong_set, correct_set],
                    "has_more": False,
                },
            }
        )

        self.assertIs(
            client.get_printing("SLD", None, "Amunet, Tyrants' End"),
            correct_set,
        )


if __name__ == "__main__":
    unittest.main()
