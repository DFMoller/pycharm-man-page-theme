import unittest

from inventory import Category, Item, parse_line


class ParseLineTest(unittest.TestCase):
    def test_valid_line_gives_item(self) -> None:
        self.assertEqual(parse_line("ABC-0001,2,3.5"), Item("ABC-0001", Category.PART, 2, 3.5))

    def test_invalid_sku_is_skipped(self) -> None:
        self.assertIsNone(parse_line("abc,2,3.5"))

    def test_deliberate_failure_for_screenshots(self) -> None:
        # Fails on purpose, so the test runner shows a failed test in the screenshot.
        self.assertEqual(parse_line("ABC-0002,1,1.0").quantity, 2)
