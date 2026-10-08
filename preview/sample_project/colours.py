"""Print the 16 ANSI colours so the run console shows the editor scheme's console colours."""

NAMES = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "gray"]

for offset, label in ((30, "normal"), (90, "bright")):
    cells = [f"\033[{offset + index}m{name:>8}\033[0m" for index, name in enumerate(NAMES)]
    print(f"{label:>6}: " + " ".join(cells))
print("\033[1mbold\033[0m \033[4munderline\033[0m plain")
