#!/bin/bash
# 输出当前 LUNA 网站隧道地址
LOGDIR=/opt/data/luna/.service-logs
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGDIR/tunnel-luna.log" 2>/dev/null | tail -1)
echo "$URL"
