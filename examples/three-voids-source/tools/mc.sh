#!/bin/bash
# mc.sh focus | chat "text" | key K... | log [n]
I="/home/n/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/1.21.4(1)/minecraft"
WID=$(wmctrl -l | grep "Minecraft 1.21.4" | awk '{print $1}')
case "$1" in
 focus) wmctrl -ia $WID; sleep 0.4;;
 chat) wmctrl -ia $WID; sleep 0.3; xdotool key t; sleep 0.4; xdotool type --delay 15 "$2"; sleep 0.2; xdotool key Return; sleep 0.3;;
 key) shift; wmctrl -ia $WID; sleep 0.2; xdotool key "$@";;
 log) tail -n ${2:-15} "$I/logs/latest.log" | cut -c1-600;;
esac
