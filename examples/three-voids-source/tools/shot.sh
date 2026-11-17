#!/bin/bash
# shot.sh out.jpg [scale_w] -> screenshot of DP-0 monitor (Minecraft)
ffmpeg -loglevel error -y -f x11grab -video_size 2560x1080 -i :0.0+1080,1080 -frames:v 1 -vf scale=${2:-1280}:-1 "$1"
