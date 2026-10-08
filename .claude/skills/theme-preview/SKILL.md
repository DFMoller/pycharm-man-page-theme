---
name: theme-preview
description: How to design and change the Man Page PyCharm theme with the closed check-and-preview loop - edit colors, run check_theme.py, take sandboxed PyCharm screenshots with preview.py, crop and compare them, and report what changed. Use whenever changing colors in make_theme.py or ManPage.xml, investigating how part of the PyCharm UI looks in the theme, adding a preview scene, or when preview.py fails.
---

# Designing the theme with the preview loop

Never report a color change as done from the code alone. Look at it: every change goes through the
static check and at least one screenshot, and the reply says what the screenshot showed.

## Design intent

The theme copies the Ubuntu terminal's "Man page" profile: pale yellow `#FEF49C` content, black text,
flat surfaces with no colored frames. Purple is a splash only: the header bar is one solid lavender
band (`#7F7ACD`, the terminal's title bar color in an SSH session), and purple otherwise appears only
as accents (primary buttons, checkboxes, focus rings, light lavender selection). Tool window strips,
gaps between panels, the window frame and the status bar stay yellow. Keep to this when changing
colors.

The header bar has no background of its own: the window frame painter fills it with
`MainToolbar.background`, and fills strips and gaps with `MainWindow.background`. The project-color
gradient is switched off (zero size), which is what lets the two differ; see `GRADIENT_PATTERNS` in
`make_theme.py`. Check header changes in both an active window (`main`) and an inactive one
(`settings`, where the dialog has focus).

## Where the colors live

- `make_theme.py` generates `src/themes/ManPage.theme.json` from Islands Light in the installed
  PyCharm. Do not edit the generated JSON by hand; `build.sh` (and so `preview.py`) overwrites it.
  - `NEW_COLORS` - named palette colors added to the theme (paper, lavender, purple, ...).
  - `GREY_RAMP` - the light end of the Islands grey ramp, remapped to yellows.
  - `GRADIENT_PATTERNS` - flattens the header bar's project-color gradient to lavender.
  - `REPLACEMENTS` - exact text edits to the source theme. Each `old` string must match exactly once,
    or `make_theme.py` fails and names it. Copy the `old` text from the source theme, including its
    indentation and line breaks.
- `ManPage.xml` - the editor color scheme: editor, gutter, caret row, selection, console ANSI colors.
  Attributes not set here come from the parent `Default` scheme.

To find the key that paints a UI element, search the theme for candidate names before guessing:

```bash
python3 -c "import json,sys; from check_theme import flatten; t=json.load(open('src/themes/ManPage.theme.json')); \
[print(k,'=',v) for k,v in flatten(t).items() if sys.argv[1].lower() in k.lower()]" Stripe
```

Keys under `ui` resolve through the `colors` palette (`"MainToolbar.background": "lavender"`), and a
`*.` key (for example `*.selectionBackground`) is the default for every component.

## The loop

1. Before changing anything, keep a "before" screenshot of the scene the change affects:
   `./preview.py <scene> && cp preview/out/<scene>.png preview/out/<scene>.before.png`.
   Skip this if a current screenshot of that scene already exists from this session.
2. Make the change.
3. Run `./check_theme.py`. It takes about 0.1 s. Read the contrast lines for the pairs you touched; a
   new `FAIL`, or a ratio that dropped, needs a reason or a fix. The diff at the end shows the theme
   keys that now differ from Islands Light; check that your change appears there and nothing else
   changed by accident. Every pair passes today, so exit status 1 means your change broke one. A pair
   may stay below its minimum only with a reason in `EXCEPTIONS` in `check_theme.py` (reported as
   `exc`); add one only when the user agrees.
4. Run `./preview.py <scene>` and read the PNG it prints. A run takes 25 to 40 s.
5. Look closely at the area you changed (see "Looking at details"). Compare it with the before
   screenshot.
6. Repeat from 2 until it looks right, then run any other scene that shows the same keys.

Several scenes in a row are fine, but run them one at a time in the foreground; two previews at once
share the sandbox folder and break each other.

## Choosing a scene

- `main` - header bar, tool window strips, Project tree with selection, editor, status bar. Use for most
  UI and editor changes.
- `settings` - Settings dialog on the Appearance page: tree, form controls, checkboxes, buttons. Use for
  dialogs, controls and the accent color.
- `popup` - Search Everywhere with a selected result. Use for popups, text fields and list selection.
- `menu` - the File menu, opened from the main menu. Use for menus, separators and shortcut text.
- `run` - Run tool window with the 16 ANSI colors, bold and underline. Use for console colors in
  `ManPage.xml`.

The editor shows `preview/sample_project/inventory.py`, which has keywords, strings, numbers,
decorators, type hints, docstrings, comments, an unused variable and inlay hints.

## Looking at details

The screen is 1920x1200. A full screenshot is scaled down when read, so crop before judging thin lines,
small text or icons:

```bash
convert preview/out/main.png -crop 700x300+0+0 preview/out/crop.png                    # region
convert preview/out/main.before.png preview/out/main.png -crop 700x300+0+0 +append preview/out/side.png
convert preview/out/main.png -crop 1x1+20+500 -format '%[hex:p{0,0}]' info:            # one pixel
```

The `+append` line puts before and after side by side; read `side.png`. Sampling a pixel tells you
the exact color the IDE painted, which is how to confirm which key is in effect.

Rough regions in the `main` scene: header bar `y 0-40`; left tool window strip `x 0-40`; Project tool
window `x 40-670`; editor tabs `y 45-80` right of the Project tool window; status bar `y 1170-1200`.
In the `run` scene the console starts at about `y 780`.

Things to check every time:

- Text and icons on the changed background are easy to read, including disabled and secondary text.
- Selection, hover and focus states still stand out from the background around them.
- Borders and separators between panels are still visible, but not loud.
- Nothing else in the screenshot changed that you did not mean to change.

## Reporting back

Say what you changed, which scenes you looked at, and what you saw, with the contrast ratios of the
pairs you touched. Mention anything that looks wrong even if it is outside the request. The user cannot
see the screenshots unless you show them; offer the path in `preview/out/`.

Before the user installs a build by hand, bump `<version>` in `src/META-INF/plugin.xml`.

## Adding a scene

Scenes are in `SCENES` in `preview.py`. Each `Step` is a list of key chords, sent together, then a
pause before the script waits for the screen to settle again. Chord names are `java.awt.event.KeyEvent`
constants without `VK_`, joined with `+`, plus `ctrl` and `esc` (for example `ctrl+shift+f10`). Most
scenes start with `SHOW_PROJECT`; if a step needs the editor to have keyboard focus, put
`SHOW_PROJECT` after it, because the Project tool window takes the focus. Add the scene to the list
under "Choosing a scene".

## When preview.py fails

- "did not open the project before the timeout": read `~/.cache/manpage-theme-preview/log/idea.log`.
  After a PyCharm upgrade the ready message in `READY_MARKER` may have changed; find the new
  post-startup message in the log.
- "screen did not settle": read the screenshot it left. A dialog may be waiting, or something animates.
  Small changes such as a blinking caret are already allowed (`CARET_PIXELS`).
- `make_theme.py` names a key that no longer matches: Islands Light changed in the new PyCharm. Update
  the `REPLACEMENTS` entry from the new source theme.
- Keys seem to do nothing: the click at the top of the screen that gives the IDE focus (in
  `preview/Keys.java`) may be missing the header bar.

## Safety rules

- Never start the sandbox IDE or `preview/Keys.java` with `WAYLAND_DISPLAY` or `XDG_SESSION_TYPE`
  set, and never remove the guards against it. With either set, the IDE opens on the user's real
  screen and `java.awt.Robot` asks for screen sharing through the desktop portal.
- If the user reports a screen-sharing or remote-desktop dialog, stop all previews and investigate
  before running anything else.
- Never use the native launcher `bin/pycharm` for the sandbox; it uses the user's own IDE.
- `~/.cache/manpage-theme-preview` contains a copy of the user's PyCharm config, including the
  licence. Never copy anything from it into the repository.
