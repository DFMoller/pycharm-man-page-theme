#!/usr/bin/env python3
"""Build the theme, show it in a throwaway PyCharm on a virtual display, and save a screenshot.

The IDE runs on its own Xvfb display, so nothing appears on the desktop, and with its own config,
plugins, system and log directories under ~/.cache/manpage-theme-preview, so the user's own PyCharm
is never touched. The sandbox config is a copy of the user's PyCharm config, which already holds the
accepted user agreement and licence, so no first-run dialogs appear. The files in preview/config are
then copied over it to select the theme, open the sample project and keep the screen still.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
PREVIEW = REPO / "preview"
CONFIG_OVERRIDES = PREVIEW / "config"
SAMPLE_PROJECT = PREVIEW / "sample_project"
KEYS_HELPER = PREVIEW / "Keys.java"
OUT_DIR = PREVIEW / "out"

SANDBOX = Path.home() / ".cache" / "manpage-theme-preview"
SANDBOX_PROJECT = SANDBOX / "project"
SANDBOX_LOG = SANDBOX / "log"
# Matches the frame size in preview/config/options.
SCREEN = "1920x1200x24"
PREVIEW_PYTHON = "/usr/bin/python3"

# Per-project state in the user's config. The sandbox gets its own from preview/config/workspace.
SKIPPED_CONFIG = {"workspace"}
# Bundled plugins disabled in the sandbox. Backup and Sync could otherwise push the sandbox's theme
# choice to the user's JetBrains account, and from there into their real IDE.
DISABLED_PLUGINS = ["com.intellij.settingsSync"]

# Environment variables that make Java use the user's Wayland desktop instead of the virtual display.
WAYLAND_VARIABLES = ("WAYLAND_DISPLAY", "XDG_SESSION_TYPE")

# Logged once the project frame is open and its startup activities have run.
READY_MARKER = "Post-startup activities under progress took"
# Seconds between screenshots while waiting for the screen to settle, and how many identical
# screenshots in a row count as settled.
POLL_INTERVAL = 1.5
STABLE_COUNT = 3
# Screenshots that differ by at most this many pixels count as the same. Text fields in dialogs and
# popups have a blinking caret, which the editor's caret setting does not cover.
CARET_PIXELS = 200


@dataclass(frozen=True)
class Step:
    """Keys to press in one go, then a pause before waiting for the screen to settle again.

    Each entry in keys is a chord such as "ctrl+alt+s"; see preview/Keys.java for the names.
    """

    keys: list[str]
    pause: float = 1.0


# Every scene starts from the main window with inventory.py open and the Project tool window shown.
# Setting the tool window layout in preview/config would drop the other tool window buttons, so the
# Project tool window is opened with its shortcut instead.
SHOW_PROJECT = Step(["alt+1"])
SCENES: dict[str, list[Step]] = {
    "main": [SHOW_PROJECT],
    "settings": [SHOW_PROJECT, Step(["ctrl+alt+s"], pause=3.0)],
    "popup": [SHOW_PROJECT, Step(["shift", "shift"], pause=2.0)],
    "menu": [SHOW_PROJECT, Step(["alt+f"])],
    # From the editor, switch to the colours.py tab and run it, so the console shows the ANSI colours.
    # The Project tool window comes last, because it takes the keyboard focus from the editor.
    "run": [Step(["alt+left"]), Step(["ctrl+shift+f10"], pause=6.0), SHOW_PROJECT],
}


class PreviewError(RuntimeError):
    """The preview could not be produced; the message says why."""


def newest_pycharm() -> Path:
    """Return the newest PyCharm install under /opt.

    Raises
    ------
    PreviewError
        If no install is found.
    """
    installs = [path for path in Path("/opt").glob("pycharm-*") if re.fullmatch(r"pycharm-[\d.]+", path.name)]
    if not installs:
        raise PreviewError("No PyCharm install found under /opt; pass --pycharm.")
    return max(installs, key=lambda path: [int(part) for part in path.name[len("pycharm-"):].split(".")])


def user_config_dir(pycharm: Path) -> Path:
    """Return the user's config directory for this PyCharm, e.g. ~/.config/JetBrains/PyCharm2026.1.

    Raises
    ------
    PreviewError
        If the directory does not exist, which means this PyCharm has never been started.
    """
    match = re.search(r'"dataDirectoryName":\s*"([^"]+)"', (pycharm / "product-info.json").read_text())
    if not match:
        raise PreviewError(f"No dataDirectoryName in {pycharm / 'product-info.json'}.")
    config = Path.home() / ".config" / "JetBrains" / match.group(1)
    if not config.is_dir():
        raise PreviewError(f"User config {config} not found; start this PyCharm once by hand first.")
    return config


def prepare_sandbox(pycharm: Path, jar: Path) -> dict[str, str]:
    """Rebuild the sandbox config, plugins, project and log, and keep its caches between runs.

    Returns
    -------
    dict[str, str]
        Environment variables that point the PyCharm launcher at the sandbox.
    """
    config = SANDBOX / "config"
    plugins = SANDBOX / "plugins"
    for path in (config, plugins, SANDBOX_PROJECT, SANDBOX_LOG):
        shutil.rmtree(path, ignore_errors=True)

    user_config = user_config_dir(pycharm)
    shutil.copytree(user_config, config, ignore=lambda d, _: SKIPPED_CONFIG if Path(d) == user_config else set())
    for source in CONFIG_OVERRIDES.rglob("*.xml"):
        text = source.read_text()
        text = text.replace("$PREVIEW_PROJECT$", str(SANDBOX_PROJECT)).replace("$PREVIEW_PYTHON$", PREVIEW_PYTHON)
        target = config / source.relative_to(CONFIG_OVERRIDES)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    disabled = config / "disabled_plugins.txt"
    existing = disabled.read_text().split() if disabled.exists() else []
    disabled.write_text("\n".join(dict.fromkeys(existing + DISABLED_PLUGINS)) + "\n")

    plugins.mkdir()
    shutil.copy2(jar, plugins)
    shutil.copytree(SAMPLE_PROJECT, SANDBOX_PROJECT)
    SANDBOX_LOG.mkdir()

    properties = SANDBOX / "idea.properties"
    folders = ("config", "plugins", "system", "log")
    properties.write_text("".join(f"idea.{name}.path={SANDBOX / name}\n" for name in folders))
    # On a Wayland desktop the IDE picks its native Wayland toolkit, which ignores DISPLAY and opens the
    # window on the user's screen. Force X11 so it draws on the virtual display; virtual_display_env
    # removes the Wayland variables as well.
    vm_options = SANDBOX / "pycharm64.vmoptions"
    vm_options.write_text("-Dawt.toolkit.name=XToolkit\n")
    return {"PYCHARM_PROPERTIES": str(properties), "PYCHARM_VM_OPTIONS": str(vm_options)}


def start_xvfb() -> tuple[subprocess.Popen, str]:
    """Start Xvfb on a free display and return the process and its DISPLAY value.

    Raises
    ------
    PreviewError
        If Xvfb does not start.
    """
    read_fd, write_fd = os.pipe()
    xvfb = subprocess.Popen(
        ["Xvfb", "-displayfd", str(write_fd), "-screen", "0", SCREEN, "-nolisten", "tcp"],
        pass_fds=(write_fd,),
        stderr=subprocess.DEVNULL,
    )
    os.close(write_fd)
    with os.fdopen(read_fd) as reader:
        number = reader.readline().strip()
    if not number:
        xvfb.kill()
        raise PreviewError("Xvfb did not report a display number.")
    return xvfb, f":{number}"


def screenshot(display: str, path: Path) -> None:
    """Capture the whole virtual screen to path."""
    subprocess.run(["import", "-display", display, "-window", "root", str(path)], check=True)


def changed_pixels(first: Path, second: Path) -> int:
    """Return how many pixels differ between two images of the same size."""
    # compare prints the count on stderr and exits with 1 when the images differ.
    command = ["compare", "-metric", "AE", str(first), str(second), "null:"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode > 1:
        raise PreviewError(f"compare failed: {result.stderr.strip()}")
    return int(float(result.stderr.split()[0]))


def wait_until_settled(display: str, path: Path, deadline: float) -> None:
    """Take screenshots until STABLE_COUNT in a row are the same, apart from a blinking caret.

    Raises
    ------
    PreviewError
        If the deadline passes first. The last screenshot is left at path for diagnosis.
    """
    previous = path.with_suffix(".previous.png")
    screenshot(display, previous)
    same = 1
    try:
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL)
            screenshot(display, path)
            same = same + 1 if changed_pixels(previous, path) <= CARET_PIXELS else 1
            if same >= STABLE_COUNT:
                return
            shutil.copyfile(path, previous)
    finally:
        previous.unlink(missing_ok=True)
    raise PreviewError(f"The screen did not settle before the timeout; last screenshot: {path}")


def wait_for_ready(ide: subprocess.Popen, deadline: float) -> None:
    """Wait until the IDE log shows that the project is open.

    Raises
    ------
    PreviewError
        If the IDE exits or the deadline passes first.
    """
    log = SANDBOX_LOG / "idea.log"
    while time.monotonic() < deadline:
        if ide.poll() is not None:
            raise PreviewError(f"PyCharm exited early with status {ide.returncode}; see {SANDBOX_LOG}")
        if log.exists() and READY_MARKER in log.read_text(errors="replace"):
            return
        time.sleep(POLL_INTERVAL)
    raise PreviewError(f"PyCharm did not open the project before the timeout; see {SANDBOX_LOG}")


def virtual_display_env(display: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment in which Java programs see only the virtual X display.

    Java decides it is on Wayland from WAYLAND_DISPLAY and XDG_SESSION_TYPE, even with DISPLAY set. On
    Wayland, the IDE opens its window on the user's screen, and java.awt.Robot asks the desktop's
    Remote Desktop portal for access to the user's real screen. preview/Keys.java refuses to run if
    either variable is set.
    """
    env = {**os.environ, **(extra or {}), "DISPLAY": display}
    for name in WAYLAND_VARIABLES:
        env.pop(name, None)
    return env


def press(pycharm: Path, display: str, keys: list[str]) -> None:
    """Send key chords to the virtual display with the Java runtime bundled in PyCharm."""
    java = pycharm / "jbr" / "bin" / "java"
    # Belt and braces: also tell Robot to use plain X11, never a desktop portal.
    command = [str(java), "-Dawt.robot.screenshotMethod=x11", str(KEYS_HELPER), *keys]
    subprocess.run(command, check=True, env=virtual_display_env(display))


def stop(process: subprocess.Popen) -> None:
    """Stop a process and everything in its process group, first politely and then by force."""
    for sig, wait in ((signal.SIGTERM, 15), (signal.SIGKILL, 5)):
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(wait)
        except subprocess.TimeoutExpired:
            continue


def preview(pycharm: Path, scene: str, timeout: float) -> Path:
    """Build the plugin, show the scene and return the path of the screenshot.

    Raises
    ------
    PreviewError
        If any stage fails or times out.
    """
    subprocess.run([str(REPO / "build.sh"), str(pycharm)], check=True, stdout=subprocess.DEVNULL)
    sandbox_env = prepare_sandbox(pycharm, REPO / "ManPageTheme.jar")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shot = OUT_DIR / f"{scene}.png"
    deadline = time.monotonic() + timeout

    xvfb, display = start_xvfb()
    ide = None
    try:
        env = virtual_display_env(display, sandbox_env)
        # The native launcher (bin/pycharm) ignores PYCHARM_PROPERTIES and would hand the project to the
        # user's running IDE, so the script launcher is used.
        with open(SANDBOX_LOG / "stdout.log", "w") as out:
            ide = subprocess.Popen(
                [str(pycharm / "bin" / "pycharm.sh"), str(SANDBOX_PROJECT)],
                env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True,
            )
        wait_for_ready(ide, deadline)
        wait_until_settled(display, shot, deadline)
        for step in SCENES[scene]:
            press(pycharm, display, step.keys)
            time.sleep(step.pause)
            wait_until_settled(display, shot, deadline)
    finally:
        if ide is not None:
            stop(ide)
        xvfb.terminate()
        xvfb.wait()
    return shot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scene", nargs="?", default="main", choices=SCENES, help="What to show (default: main).")
    parser.add_argument("--pycharm", type=Path, help="PyCharm install directory (default: newest /opt/pycharm-*).")
    parser.add_argument("--timeout", type=float, default=180, help="Seconds before giving up (default: 180).")
    args = parser.parse_args()
    try:
        print(preview(args.pycharm or newest_pycharm(), args.scene, args.timeout))
    except PreviewError as error:
        sys.exit(f"preview: {error}")


if __name__ == "__main__":
    main()
