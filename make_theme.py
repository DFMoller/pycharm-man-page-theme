"""Generate the Man Page UI theme from the Islands Light theme bundled with PyCharm.

The theme is a recoloured copy of Islands Light: backgrounds become the pale yellow of the
Ptyxis/Terminal "Man Page" palette, and lavender/purple replaces the blue accent, selection and
header colours. Everything else (text colours, icons, metrics) is inherited unchanged, which is why
the theme is regenerated from the installed IDE rather than maintained by hand.
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
    "lavender": "#7F7ACD",
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
# one painter. The header bar itself is transparent: with "Use project colors in main toolbar" on, the
# painter draws a per-project gradient over the top-left of the window (600x300px in Islands Light, which
# covers the top of the left strip too) and otherwise MainToolbar.background. The gradient is switched
# off by giving it zero size in REPLACEMENTS, so the header bar is MainToolbar.background (lavender)
# whatever the setting, and MainWindow.background can stay yellow for the strips and gaps. Every gradient
# colour is also made transparent, so nothing lavender spills onto the strip if a future IDE ignores the
# size. Each pattern must match this many times.
GRADIENT_COLOR = NEW_COLORS["lavender"] + "00"
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
    # The Run/Debug buttons in the header draw their icons in iconColor, faded when disabled; the default
    # grey fades to almost nothing on lavender. The green Run icon uses runIconColor, which Islands Light
    # leaves at the default green: the same lightness as the lavender (contrast 1.0). A dark green keeps
    # it green and gives it 3:1. It applies to the header only, not to the Run arrows in the editor.
    (
        '"iconColor": "icon-default-stroke",\n      "runningBackground"',
        '"iconColor": "#1E1F28",\n      "runIconColor": "#163D21",\n      "runningBackground"',
    ),
    # Header bar and title bar. The project-colour gradient gets zero size; see GRADIENT_PATTERNS.
    ('"MainToolbarGradient.width": 600', '"MainToolbarGradient.width": 0'),
    ('"MainToolbarGradient.height": 300', '"MainToolbarGradient.height": 0'),
    ('"MainToolbar.background": "container-main-window-bg-alt"', '"MainToolbar.background": "lavender"'),
    (
        '"MainToolbar": {\n      "background": "container-main-window-bg",\n'
        '      "inactiveBackground": "container-main-window-bg",',
        '"MainToolbar": {\n      "background": "lavender",\n      "inactiveBackground": "lavender",',
    ),
    (
        '"Icon": {\n        "background": "container-main-window-bg",',
        '"Icon": {\n        "background": "lavender",',
    ),
    (
        '"Dropdown": {\n        "foreground": "text-default",\n        "background": "container-main-window-bg",',
        '"Dropdown": {\n        "foreground": "text-default",\n        "background": "lavender",',
    ),
    (
        '"TitlePane": {\n      "background": "container-dialog-bg",\n'
        '      "inactiveBackground": "container-dialog-bg",',
        '"TitlePane": {\n      "background": "lavender",\n      "inactiveBackground": "lavender",',
    ),
    # Darken the standard grey used by the light icon set (including the GNOME window buttons), which
    # is too faint on the lavender header, and the lighter secondary grey with it, to 3:1 on lavender.
    ('"ColorPalette": {', '"ColorPalette": {\n      "#6C707E": "#333542",\n      "#818594": "#373945",'),
    # Disabled icons are a grey-filtered copy of the icon (brightness, contrast, alpha). The inherited
    # filter lightens them, which makes them vanish on the lavender header; darken them instead.
    ('"ui": {\n    "*": {', '"ui": {\n    "grayFilter": "-25,-30,100",\n    "*": {'),
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
