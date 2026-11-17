#!/bin/bash
# launch.sh <server-host>  — (re)start the Minecraft client into a server
pkill -9 -f 'instances/1.21.4\(1\)/natives'; sleep 3
(setsid flatpak run org.prismlauncher.PrismLauncher --launch "1.21.4(1)" --server "$1" >/dev/null 2>&1 &)
for i in $(seq 40); do sleep 3; wmctrl -l | grep -q "Minecraft 1.21.4 - Multiplayer" && break; done
sleep 6; cd "$(dirname "$0")/.."; python3 tools/mcctl.py state
