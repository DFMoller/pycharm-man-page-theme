#!/usr/bin/env bash
# Regenerate the theme from the installed PyCharm and package it as a plugin jar.
# Usage: ./build.sh [pycharm-install-dir]
set -euo pipefail

cd "$(dirname "$0")"
pycharm_dir="${1:-$(ls -d /opt/pycharm-* | sort -V | tail -1)}"

python3 make_theme.py "$pycharm_dir"
cp ManPage.xml src/themes/ManPage.xml
rm -f ManPageTheme.jar
(cd src && zip -qr ../ManPageTheme.jar META-INF themes)
echo "Built $(pwd)/ManPageTheme.jar from $pycharm_dir"
