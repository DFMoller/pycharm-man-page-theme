# PyCharm Man Page theme

A PyCharm UI theme and editor color scheme. See `README.md` for what each file does.

## Seeing the result of a change

Never report a color change as done without looking at it. After changing colors in `make_theme.py`
or `ManPage.xml`, run `./check_theme.py` (contrast and keys changed, no IDE) and `./preview.py [scene]`
(screenshot of a sandboxed PyCharm with the theme), then read the PNG. The `theme-preview` skill in
`.claude/skills/` has the full workflow: scenes, cropping and comparing screenshots, finding theme
keys, and what to do when a preview fails.

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
