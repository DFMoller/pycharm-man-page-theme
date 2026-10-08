# PyCharm Man Page theme

A PyCharm UI theme and editor color scheme that match the Ptyxis/Terminal "Man Page" palette: pale
yellow backgrounds and header bar, and purple accent and lavender selection colors.

The UI theme is generated from the Islands Light theme bundled with PyCharm, so it inherits all
layout and icon settings and only changes colors.

## Files

- `make_theme.py` - reads Islands Light from the PyCharm install and writes the recolored theme to
  `src/themes/ManPage.theme.json`. Edit the color tables at the top of this file to change shades.
- `ManPage.xml` - the editor color scheme (editor background, selection, console ANSI colors).
- `src/META-INF/plugin.xml` - plugin descriptor. Bump `<version>` before reinstalling a new build.
- `build.sh` - regenerates the theme and packages `ManPageTheme.jar`.
- `check_theme.py` - checks contrast of the main color pairs and lists the keys changed from Islands
  Light, without starting PyCharm.
- `preview.py` - shows the theme in a throwaway PyCharm on a virtual display and saves a screenshot.
- `preview/` - the sample project, sandbox settings and key-press helper that `preview.py` uses.

## Build and install

```bash
./build.sh                         # uses the newest /opt/pycharm-* install
./build.sh /opt/pycharm-2026.1.2   # or name the install explicitly
```

In PyCharm: Settings > Plugins > gear icon > Install Plugin from Disk, choose `ManPageTheme.jar`,
restart, then select "Man Page" under Settings > Appearance & Behavior > Appearance > Theme.

If `make_theme.py` fails after a PyCharm upgrade, the upstream Islands Light theme has changed; the
error names the key that no longer matches.

## Checking a change without installing it

```bash
./check_theme.py          # contrast report and diff against Islands Light; exit status 1 on low contrast
./preview.py              # screenshot of the editor; prints the path of the PNG
./preview.py settings     # other scenes: settings, popup, menu, run
```

`preview.py` runs `build.sh`, then starts PyCharm on its own Xvfb display, so no window appears on the
desktop. The IDE uses separate config, plugins, cache and log directories under
`~/.cache/manpage-theme-preview`, so the PyCharm you work in is not changed and can stay open. The
sandbox config starts as a copy of your PyCharm config, so PyCharm must have been started by hand at
least once. Screenshots go to `preview/out/`.

The preview needs `Xvfb` and ImageMagick (`sudo apt install xvfb imagemagick`). Key presses for the
scenes are sent by `preview/Keys.java`, run with the Java runtime bundled in PyCharm.

Run the unit tests with `python3 -m unittest discover -s tests -t .`.
