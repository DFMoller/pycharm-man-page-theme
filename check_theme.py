#!/usr/bin/env python3
"""Check the generated theme without starting PyCharm: contrast of key colour pairs, and keys changed.

The contrast check computes the WCAG 2 contrast ratio of the foreground/background pairs listed below,
for the UI theme (src/themes/ManPage.theme.json) and the editor scheme (ManPage.xml). It exits with
status 1 if any pair is below its limit. Pairs whose keys the theme does not set are skipped, because
their colours come from the parent theme, which this script does not load.

The diff lists the theme keys whose values differ from the Islands Light theme bundled with PyCharm.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path

from make_theme import read_islands_light
from preview import newest_pycharm

REPO = Path(__file__).resolve().parent
THEME = REPO / "src" / "themes" / "ManPage.theme.json"
SCHEME = REPO / "ManPage.xml"

# WCAG 2 minimums: 4.5 for normal text, 3.0 for icons, large text and secondary decoration.
TEXT = 4.5
NON_TEXT = 3.0

# (label, foreground, background, minimum). Colours are UI keys (dotted, e.g. "MainToolbar.foreground"),
# other theme keys with their section (e.g. "icons.ColorPalette.#6C707E", the colour that the icon grey
# #6C707E is replaced with), names from the theme's colour palette, or literal hex values.
UI_PAIRS = [
    ("Dialog text", "text-default", "*.background", TEXT),
    ("Secondary text in dialogs", "text-secondary", "*.background", TEXT),
    ("Links in dialogs", "text-link", "*.background", TEXT),
    ("Selected list and tree text", "*.selectionForeground", "*.selectionBackground", TEXT),
    ("Header bar text", "MainToolbar.foreground", "MainToolbar.background", TEXT),
    ("Header bar dropdown text", "MainToolbar.Dropdown.foreground", "MainToolbar.Dropdown.background", TEXT),
    # The light icon set's main grey, which the theme does not remap.
    ("Header icons", "#6C707E", "MainToolbar.background", NON_TEXT),
    ("Header secondary icons", "icons.ColorPalette.#818594", "MainToolbar.background", NON_TEXT),
    ("Header Run widget icons", "RunWidget.iconColor", "MainToolbar.background", NON_TEXT),
    ("Header Run icon", "RunWidget.runIconColor", "MainToolbar.background", NON_TEXT),
    ("Tool window text", "text-default", "ToolWindow.background", TEXT),
    ("Tool window buttons", "ToolWindow.Button.foreground", "ToolWindow.Stripe.background", NON_TEXT),
    ("Status bar widgets", "StatusBar.Widget.foreground", "StatusBar.background", TEXT),
    ("Popup text", "text-default", "Popup.background", TEXT),
    ("Popup footer text", "Popup.Advertiser.foreground", "Popup.Advertiser.background", TEXT),
]

# (label, foreground, background, minimum). Names are options in the scheme's <colors> section, or
# "TEXT.FOREGROUND"-style references into its <attributes> section.
EDITOR_PAIRS = [
    ("Editor text", "TEXT.FOREGROUND", "TEXT.BACKGROUND", TEXT),
    ("Editor text on the caret row", "TEXT.FOREGROUND", "CARET_ROW_COLOR", TEXT),
    ("Selected editor text", "TEXT.FOREGROUND", "SELECTION_BACKGROUND", TEXT),
    ("Line numbers", "LINE_NUMBERS_COLOR", "GUTTER_BACKGROUND", NON_TEXT),
    ("Caret row line number", "LINE_NUMBER_ON_CARET_ROW_COLOR", "GUTTER_BACKGROUND", TEXT),
]
# Every CONSOLE_*_OUTPUT foreground in the scheme is checked against the console background.
CONSOLE_BACKGROUND = "CONSOLE_BACKGROUND_KEY"
CONSOLE_MINIMUM = NON_TEXT

# Pairs allowed to stay below their minimum, by label, with the reason. They are reported but do not fail
# the check.
EXCEPTIONS = {
    "Console white": "ANSI bright white is meant to be lighter than a light background; programs use it on "
    "coloured backgrounds. Making it readable on paper would turn it into another grey.",
}

HEX = re.compile(r"#?([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?")


@dataclass(frozen=True)
class Result:
    """One checked colour pair."""

    label: str
    foreground: str
    background: str
    ratio: float
    minimum: float

    @property
    def passed(self) -> bool:
        return self.ratio >= self.minimum or self.label in EXCEPTIONS


def flatten(tree: dict, prefix: str = "") -> dict[str, object]:
    """Flatten nested theme sections into dotted keys, e.g. {"A": {"b": 1}} into {"A.b": 1}."""
    flat: dict[str, object] = {}
    for key, value in tree.items():
        if isinstance(value, dict):
            flat.update(flatten(value, f"{prefix}{key}."))
        else:
            flat[f"{prefix}{key}"] = value
    return flat


def resolve(reference: str, ui: dict[str, object], palette: dict[str, str]) -> str | None:
    """Follow a UI key or palette name to a hex colour, or return None if the theme does not set it.

    Raises
    ------
    ValueError
        If the palette refers to itself in a loop.
    """
    value = ui.get(reference, reference)
    seen: set[str] = set()
    while isinstance(value, str) and value in palette:
        if value in seen:
            raise ValueError(f"Palette loop at {value!r} while resolving {reference!r}.")
        seen.add(value)
        value = palette[value]
    if isinstance(value, str) and HEX.fullmatch(value):
        return value if value.startswith("#") else f"#{value}"
    return None


def channels(colour: str) -> tuple[list[float], float]:
    """Split "#RRGGBB" or "#RRGGBBAA" into 0..1 RGB channels and alpha."""
    match = HEX.fullmatch(colour)
    if not match:
        raise ValueError(f"Not a hex colour: {colour!r}")
    rgb = [int(match.group(1)[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    alpha = int(match.group(2), 16) / 255 if match.group(2) else 1.0
    return rgb, alpha


def luminance(rgb: list[float]) -> float:
    """Relative luminance as defined by WCAG 2."""
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    """WCAG 2 contrast ratio. A translucent foreground is first blended over the background."""
    back, _ = channels(background)
    front, alpha = channels(foreground)
    front = [alpha * f + (1 - alpha) * b for f, b in zip(front, back)]
    lighter, darker = sorted((luminance(front), luminance(back)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def scheme_colours(scheme: ElementTree.Element) -> dict[str, str]:
    """Return the scheme's colours as "#RRGGBB" by name: <colors> options, and "ATTRIBUTE.FIELD" entries."""
    colours: dict[str, str] = {}
    for option in scheme.findall("./colors/option"):
        if option.get("value"):
            colours[option.get("name")] = "#" + option.get("value")
    for attribute in scheme.findall("./attributes/option"):
        for field in attribute.findall("./value/option"):
            if field.get("value"):
                colours[f"{attribute.get('name')}.{field.get('name')}"] = "#" + field.get("value").zfill(6)
    return colours


def check_ui(theme: dict) -> list[Result]:
    ui = {**flatten(theme), **flatten(theme.get("ui", {}))}
    palette = theme.get("colors", {})
    results = []
    for label, fg, bg, minimum in UI_PAIRS:
        front, back = resolve(fg, ui, palette), resolve(bg, ui, palette)
        if front and back:
            results.append(Result(label, front, back, contrast(front, back), minimum))
    return results


def check_editor(scheme: ElementTree.Element) -> list[Result]:
    colours = scheme_colours(scheme)
    pairs = list(EDITOR_PAIRS)
    for name in sorted(colours):
        if re.fullmatch(r"CONSOLE_\w+_OUTPUT\.FOREGROUND", name):
            pairs.append((f"Console {name.split('.')[0][8:-7].lower().replace('_', ' ')}", name, CONSOLE_BACKGROUND,
                          CONSOLE_MINIMUM))
    results = []
    for label, fg, bg, minimum in pairs:
        if fg in colours and bg in colours:
            results.append(Result(label, colours[fg], colours[bg], contrast(colours[fg], colours[bg]), minimum))
    return results


def theme_diff(base: dict, theme: dict) -> list[str]:
    """Describe every key whose value differs between two themes, one line each."""
    old, new = flatten(base), flatten(theme)
    lines = []
    for key in sorted(old.keys() | new.keys()):
        if key not in new:
            lines.append(f"- {key}: {old[key]}")
        elif key not in old:
            lines.append(f"+ {key}: {new[key]}")
        elif old[key] != new[key]:
            lines.append(f"~ {key}: {old[key]} -> {new[key]}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pycharm", type=Path, help="PyCharm install for the diff (default: newest /opt/pycharm-*).")
    parser.add_argument("--no-diff", action="store_true", help="Only run the contrast check.")
    args = parser.parse_args()

    theme = json.loads(THEME.read_text())
    results = check_ui(theme) + check_editor(ElementTree.parse(SCHEME).getroot())
    print("Contrast (WCAG 2 ratio, minimum in brackets):")
    for result in results:
        mark = "FAIL" if not result.passed else "ok  " if result.ratio >= result.minimum else "exc "
        print(f"  {mark} {result.ratio:5.2f} ({result.minimum}) {result.label}: "
              f"{result.foreground} on {result.background}")
    for label, reason in EXCEPTIONS.items():
        print(f"  exc: {label}: {reason}")

    if not args.no_diff:
        pycharm = args.pycharm or newest_pycharm()
        lines = theme_diff(json.loads(read_islands_light(pycharm)), theme)
        print(f"\nKeys that differ from Islands Light in {pycharm} ({len(lines)}):")
        for line in lines:
            print(f"  {line}")

    failed = [result for result in results if not result.passed]
    if failed:
        sys.exit(f"\n{len(failed)} of {len(results)} colour pairs are below their minimum contrast.")


if __name__ == "__main__":
    main()
