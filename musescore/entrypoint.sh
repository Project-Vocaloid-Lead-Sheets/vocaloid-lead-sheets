#!/bin/sh
set -e

Xvfb :99 -screen 0 1920x1080x24 >/tmp/xvfb.log 2>&1 &
export DISPLAY=:99

sleep 1

exec /opt/musescore/AppRun "$@"
