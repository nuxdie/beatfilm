#!/bin/bash
# waitday.sh [max_tries=24] — poll sky every 25 s until DAY
cd /home/n/Videos/three-voids
for i in $(seq ${1:-24}); do r=$(python3 tools/scout.py sky 2>&1 | tail -1); echo "$(date +%T) $r"; [[ "$r" == *" DAY" ]] && exit 0; sleep 25; done; exit 1
