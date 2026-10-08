# PyCharm Man Page theme

A PyCharm UI theme and editor color scheme. See `README.md` for what each file does.

## Seeing the result of a change

After changing colors in `make_theme.py` or `ManPage.xml`, check the result yourself before reporting
back:

1. `./check_theme.py` - contrast of the main color pairs and the keys that differ from Islands Light.
   Takes well under a second and needs no IDE. Exit status 1 means a pair is below its minimum; say which.
2. `./preview.py [scene]` - builds the jar, starts a throwaway PyCharm on a virtual display with the
   theme active, and prints the path of a screenshot. Read the PNG to see the result. Scenes: `main`
   (default; editor and Project tool window), `settings`, `popup` (Search Everywhere), `menu` (File
   menu), `run` (run console with the 16 ANSI colors). A cached run takes 25 to 40 s; the first run
   after a PyCharm upgrade takes about a minute.
3. To look at a detail, crop the screenshot with ImageMagick (`convert in.png -crop WxH+X+Y out.png`)
   and read the crop.

Run the unit tests with `python3 -m unittest discover -s tests -t .`.

## Rules for the preview

- Never start the sandbox IDE or `preview/Keys.java` with `WAYLAND_DISPLAY` or `XDG_SESSION_TYPE` set.
  With either set, Java uses the real desktop: the IDE window appears on the user's screen, and
  `java.awt.Robot` asks for screen sharing through the desktop portal. `preview.py` removes both, and
  `Keys.java` refuses to run if they are set. Do not work around either safeguard.
- Never start the sandbox with the native launcher `bin/pycharm`. It ignores `PYCHARM_PROPERTIES` and
  uses the user's own config and running IDE.
- The sandbox lives in `~/.cache/manpage-theme-preview` and holds a copy of the user's PyCharm config,
  including their licence. Do not copy anything from it into the repository.
- If a run fails, the IDE log is in `~/.cache/manpage-theme-preview/log/idea.log` and the last
  screenshot is left in `preview/out/`.
