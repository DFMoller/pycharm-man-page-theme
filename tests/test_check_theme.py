import unittest
import xml.etree.ElementTree as ElementTree

from check_theme import contrast, flatten, resolve, scheme_colours, theme_diff


class ContrastTest(unittest.TestCase):
    def test_black_on_white_is_maximum(self) -> None:
        self.assertAlmostEqual(contrast("#000000", "#FFFFFF"), 21.0, places=2)

    def test_same_colour_is_minimum(self) -> None:
        self.assertAlmostEqual(contrast("#7F7FCC", "#7F7FCC"), 1.0)

    def test_order_of_colours_does_not_matter(self) -> None:
        self.assertAlmostEqual(contrast("#FEF49C", "#333333"), contrast("#333333", "#FEF49C"))

    def test_transparent_foreground_has_no_contrast(self) -> None:
        self.assertAlmostEqual(contrast("#00000000", "#FEF49C"), 1.0)

    def test_half_transparent_foreground_is_blended(self) -> None:
        self.assertAlmostEqual(contrast("#00000080", "#FFFFFF"), contrast("#7F7F7F", "#FFFFFF"), places=1)


class ResolveTest(unittest.TestCase):
    palette = {"paper": "#FEF49C", "layer-bg": "paper"}

    def test_ui_key_follows_palette_chain(self) -> None:
        self.assertEqual(resolve("Panel.background", {"Panel.background": "layer-bg"}, self.palette), "#FEF49C")

    def test_palette_name_resolves_directly(self) -> None:
        self.assertEqual(resolve("paper", {}, self.palette), "#FEF49C")

    def test_literal_hex_without_hash_gets_one(self) -> None:
        self.assertEqual(resolve("FEF49C", {}, {}), "#FEF49C")

    def test_unset_key_gives_none(self) -> None:
        self.assertIsNone(resolve("Missing.key", {}, self.palette))

    def test_palette_loop_raises(self) -> None:
        with self.assertRaises(ValueError):
            resolve("a", {}, {"a": "b", "b": "a"})


class FlattenAndDiffTest(unittest.TestCase):
    def test_flatten_joins_nested_keys_with_dots(self) -> None:
        self.assertEqual(flatten({"A": {"b": 1, "C": {"d": 2}}, "e": 3}), {"A.b": 1, "A.C.d": 2, "e": 3})

    def test_diff_reports_changed_added_and_removed_keys(self) -> None:
        base = {"ui": {"x": "1", "gone": "2"}, "same": True}
        theme = {"ui": {"x": "9", "new": "3"}, "same": True}
        self.assertEqual(theme_diff(base, theme), ["- ui.gone: 2", "+ ui.new: 3", "~ ui.x: 1 -> 9"])


class SchemeColoursTest(unittest.TestCase):
    def test_reads_colours_and_attribute_fields(self) -> None:
        scheme = ElementTree.fromstring(
            '<scheme><colors><option name="GUTTER_BACKGROUND" value="fef49c" /></colors>'
            '<attributes><option name="TEXT"><value><option name="FOREGROUND" value="0" /></value></option>'
            "</attributes></scheme>"
        )
        self.assertEqual(scheme_colours(scheme), {"GUTTER_BACKGROUND": "#fef49c", "TEXT.FOREGROUND": "#000000"})


if __name__ == "__main__":
    unittest.main()
