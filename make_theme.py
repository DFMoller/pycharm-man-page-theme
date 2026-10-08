"""Generate the Man Page UI theme from the Islands Light theme bundled with PyCharm.

The theme is a recoloured copy of Islands Light: backgrounds become the pale yellow of the
Ptyxis/Terminal "Man Page" palette, including the header bar, and purple and lavender replace the blue
accent and selection colours. The islands layout is switched off in favour of the classic one, with
borders between panels. Everything else (text colours, icons, metrics) is inherited unchanged, which is
why the theme is regenerated from the installed IDE rather than maintained by hand.
"""

import argparse
import re
import zipfile
from pathlib import Path

ISLANDS_JAR = "lib/intellij.platform.ide.impl.jar"
ISLANDS_JSON = "themes/islands/ManyIslandsLight.theme.json"

# Named colours added to the theme palette.
NEW_COLORS = {
    "paper": "#FEF49C",
    "purple": "#5B5BB5",
    "lavender-pale": "#D4D4F2",
    "lavender-paler": "#E2E2F5",
    "lavender-border": "#B8B8E6",
}

# Light end of the grey ramp, remapped to yellows. Darker greys are used for text and stay as is.
GREY_RAMP = {
    "gray-160": "#F9EE94",
    "gray-150": "#F0E486",
    "gray-140": "#E4D87A",
    "gray-130": "#D8CC70",
    "gray-120": "#C8BD66",
    "gray-110": "#B5AB5E",
}

# The window frame (header bar, tool window strips, status bar and the gaps between panels) is painted by
# one painter. With "Use project colors in main toolbar" on, it draws a per-project colour gradient over
# the top-left of the window (600x300px in Islands Light, which covers the top of the left strip too),
# and otherwise MainToolbar.background. The gradient is switched off by giving it zero size in
# REPLACEMENTS, so the header bar is the same plain yellow as the strips whatever the setting. Every
# gradient colour is also made transparent, so nothing shows if a future IDE ignores the size. Each
# pattern must match this many times.
GRADIENT_COLOR = GREY_RAMP["gray-150"] + "00"
HEX_VALUE = r'"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?"'
GRADIENT_PATTERNS = [
    # Gradient stops of the nine project colour groups.
    (r'("grad-g\d-[a-z]+-(?:a1|a1-secondary|a2|bg)(?:-transparent)?":\s*)' + HEX_VALUE, 45),
    # White haze overlays drawn on top of the gradient.
    (r'("grad-(?:hor|ver)-[a-z]+":\s*)' + HEX_VALUE, 4),
    (r'("RecentProject\.Color\d\.MainToolbarGradientStart":\s*)' + HEX_VALUE, 9),
]

# Exact text replacements; each must match exactly once in the source theme.
REPLACEMENTS = [
    ('"name": "Islands Light"', '"name": "Man Page"'),
    ('"author": "JetBrains"', '"author": "local"'),
    ('"editorScheme": "Light"', '"editorScheme": "/themes/ManPage.xml"'),
    # Backgrounds.
    ('"layer-1-bg-inline": "white"', '"layer-1-bg-inline": "paper"'),
    ('"layer-2-bg": "white"', '"layer-2-bg": "paper"'),
    ('"container-main-window-bg-alt": "#E8E8EB"', '"container-main-window-bg-alt": "gray-150"'),
    ('"container-tool-window-bg-alt": "#F7F6F8"', '"container-tool-window-bg-alt": "gray-160"'),
    ('"container-editor-border-alt": "#E8E9ED"', '"container-editor-border-alt": "gray-140"'),
    # Secondary text (hints, popup footers, shortcuts) is mid grey in Islands Light: 3.8 on the yellow
    # backgrounds. One step darker gives 5.1, enough for small text.
    ('"text-secondary": "gray-80"', '"text-secondary": "gray-70"'),
    # Accent: buttons, focus rings, active tab underline, checkboxes.
    ('"accent-brand-bg": "blue-80"', '"accent-brand-bg": "purple"'),
    ('"accent-brand-border": "blue-80"', '"accent-brand-border": "purple"'),
    ('"accent-brand-bg-secondary": "blue-160"', '"accent-brand-bg-secondary": "lavender-paler"'),
    ('"accent-brand-border-secondary": "blue-130"', '"accent-brand-border-secondary": "lavender-border"'),
    # Selection in trees, lists, popups and toolbars.
    ('"selection-bg-active": "blue-140"', '"selection-bg-active": "lavender-pale"'),
    ('"selection-bg-active-muted": "blue-150"', '"selection-bg-active-muted": "lavender-paler"'),
    ('"tab-selected-bg-active": "blue-150"', '"tab-selected-bg-active": "lavender-paler"'),
    ('"toolbar-selected-bg": "blue-140"', '"toolbar-selected-bg": "lavender-pale"'),
    ('"toolbar-selected-bg-hovered": "blue-130"', '"toolbar-selected-bg-hovered": "lavender-border"'),
    # The green Run icon in the header uses runIconColor, which Islands Light leaves at the default green:
    # 2.9 on the yellow header. A slightly darker green gives 3.2. It applies to the header only; the Run
    # arrows in the editor gutter sit on paper, where the default green already gives 3.3.
    (
        '"iconColor": "icon-default-stroke",\n      "runningBackground"',
        '"iconColor": "icon-default-stroke",\n      "runIconColor": "#328C4A",\n      "runningBackground"',
    ),
    # Use the classic layout, with panels side by side separated by thin borders, instead of rounded
    # islands with gaps between them. Islands Light makes the borders around the tool windows, tool window
    # strips, header bar and status bar transparent (and removes the status bar's top border), because
    # islands are separated by gaps instead; the classic layout needs them back.
    ('"Islands": 1,', '"Islands": 0,'),
    (
        '"StatusBar": {\n      "background": "container-main-window-bg",\n      "borderColor": "transparent",\n'
        '      "topBorderWidth": 0,',
        '"StatusBar": {\n      "background": "container-main-window-bg",\n'
        '      "borderColor": "container-main-window-border",\n      "topBorderWidth": 1,',
    ),
    (
        '"ToolWindow": {\n      "background": "container-tool-window-bg",\n      "borderColor": "transparent",',
        '"ToolWindow": {\n      "background": "container-tool-window-bg",\n'
        '      "borderColor": "container-main-window-border",',
    ),
    (
        '"background": "container-main-window-bg",\n        "borderColor": "transparent",\n        "separatorColor"',
        '"background": "container-main-window-bg",\n        "borderColor": "container-main-window-border",\n'
        '        "separatorColor"',
    ),
    (
        '"inactiveBackground": "container-main-window-bg",\n      "borderColor": "transparent",',
        '"inactiveBackground": "container-main-window-bg",\n      "borderColor": "container-main-window-border",',
    ),
    # The project-colour gradient gets zero size; see GRADIENT_PATTERNS.
    ('"MainToolbarGradient.width": 600', '"MainToolbarGradient.width": 0'),
    ('"MainToolbarGradient.height": 300', '"MainToolbarGradient.height": 0'),
    # The light icon set's secondary grey gives 2.8 on the yellow header and strips; slightly darker
    # gives 3.3. The main icon grey already gives 3.8.
    ('"ColorPalette": {', '"ColorPalette": {\n      "#818594": "#777A88",'),
    # Checkboxes use literal colours in the colour palette section.
    ('"Checkbox.Background.Default": "#FFFFFF"', '"Checkbox.Background.Default": "#FEF49C"'),
    ('"Checkbox.Background.Disabled": "#F7F8FA"', '"Checkbox.Background.Disabled": "#F9EE94"'),
    ('"Checkbox.Background.Selected": "#3574F0"', '"Checkbox.Background.Selected": "#5B5BB5"'),
    ('"Checkbox.Border.Selected": "#3574F0"', '"Checkbox.Border.Selected": "#5B5BB5"'),
    ('"Checkbox.Focus.Wide": "#3574F0"', '"Checkbox.Focus.Wide": "#5B5BB5"'),
]


def recolour(source: str) -> str:
    """Apply the Man Page colour changes to the Islands Light theme JSON text.

    Raises
    ------
    ValueError
        If an expected key is missing, which means the upstream theme changed and the edits need
        revisiting.
    """
    for name, value in GREY_RAMP.items():
        source, count = re.subn(rf'("{name}":\s*)"#[0-9A-Fa-f]{{6}}"', rf'\1"{value}"', source, count=1)
        if count != 1:
            raise ValueError(f"Palette colour {name!r} not found in source theme.")

    new_colors = "".join(f'\n    "{name}": "{value}",' for name, value in NEW_COLORS.items())
    anchor = '"white": "#FFFFFF",'
    if source.count(anchor) != 1:
        raise ValueError("Palette anchor for new colours not found in source theme.")
    source = source.replace(anchor, anchor + new_colors)

    for pattern, expected in GRADIENT_PATTERNS:
        source, count = re.subn(pattern, rf'\1"{GRADIENT_COLOR}"', source)
        if count != expected:
            raise ValueError(f"Expected {expected} gradient colours for {pattern!r}, found {count}.")

    for old, new in REPLACEMENTS:
        if source.count(old) != 1:
            raise ValueError(f"Expected exactly one match in source theme for: {old!r}")
        source = source.replace(old, new)
    return source


def read_islands_light(pycharm_dir: Path) -> str:
    """Return the Islands Light theme JSON text bundled with a PyCharm install.

    Raises
    ------
    FileNotFoundError
        If the PyCharm install directory does not contain the bundled theme jar.
    """
    jar = pycharm_dir / ISLANDS_JAR
    if not jar.is_file():
        raise FileNotFoundError(f"Theme jar not found: {jar}")
    with zipfile.ZipFile(jar) as zf:
        return zf.read(ISLANDS_JSON).decode()


def main() -> None:
    """Write the recoloured theme JSON next to the plugin sources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pycharm_dir", type=Path, help="PyCharm install directory, e.g. /opt/pycharm-2026.1.2.")
    args = parser.parse_args()

    source = read_islands_light(args.pycharm_dir)
    out = Path(__file__).parent / "src" / "themes" / "ManPage.theme.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(recolour(source))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
