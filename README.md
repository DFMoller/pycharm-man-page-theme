# PyCharm Man Page theme

A PyCharm UI theme and editor color scheme that match the Ptyxis/Terminal "Man Page" palette: pale
yellow backgrounds, a lavender header bar, and purple accent and selection colors.

The UI theme is generated from the Islands Light theme bundled with PyCharm, so it inherits all
layout and icon settings and only changes colors.

## Files

- `make_theme.py` - reads Islands Light from the PyCharm install and writes the recolored theme to
  `src/themes/ManPage.theme.json`. Edit the color tables at the top of this file to change shades.
- `ManPage.xml` - the editor color scheme (editor background, selection, console ANSI colors).
- `src/META-INF/plugin.xml` - plugin descriptor. Bump `<version>` before reinstalling a new build.
- `build.sh` - regenerates the theme and packages `ManPageTheme.jar`.

## Build and install

```bash
./build.sh                         # uses the newest /opt/pycharm-* install
./build.sh /opt/pycharm-2026.1.2   # or name the install explicitly
```

In PyCharm: Settings > Plugins > gear icon > Install Plugin from Disk, choose `ManPageTheme.jar`,
restart, then select "Man Page" under Settings > Appearance & Behavior > Appearance > Theme.

If `make_theme.py` fails after a PyCharm upgrade, the upstream Islands Light theme has changed; the
error names the key that no longer matches.
