import unittest

from scryfall_art_downloader.parser import DeckParseError, parse_deck_list, unique_printings


class ParseDeckListTests(unittest.TestCase):
    def test_parses_exact_printing_and_special_collector_number(self):
        entries = parse_deck_list("1 Book of Mazarbul (LTR) 116\n2x Example Card (ABC) A-123")
        self.assertEqual(entries[0].name, "Book of Mazarbul")
        self.assertEqual(entries[0].set_code, "LTR")
        self.assertEqual(entries[1].quantity, 2)
        self.assertEqual(entries[1].collector_number, "A-123")

    def test_ignores_headings_comments_and_supports_sideboard_prefix(self):
        entries = parse_deck_list("Deck\n# note\nSB: 1 Negate (MOM) 68\nSideboard")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "Negate")

    def test_reports_all_bad_lines(self):
        with self.assertRaises(DeckParseError) as context:
            parse_deck_list("not a card\nalso bad")
        self.assertEqual(len(context.exception.errors), 2)

    def test_unique_printings_is_case_insensitive(self):
        entries = parse_deck_list("1 Card One (ABC) 1\n2 Card One (abc) 1")
        self.assertEqual(len(unique_printings(entries)), 1)


if __name__ == "__main__":
    unittest.main()

