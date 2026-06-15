#!/bin/bash
# 启动 LUNA 网站 Cloudflare 隧道（用 npx），禁用自动更新防止 URL 漂移
LOGFILE=/opt/data/luna/.service-logs/tunnel-luna.log
URLFILE=/nas/hermes/小天专用/助理/luna-url.txt

npx cloudflared tunnel --no-autoupdate --url http://localhost:8766 > "$LOGFILE" 2>&1 &

sleep 8
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGFILE" 2>/dev/null | tail -1)
if [ -n "$URL" ]; then
  echo "$URL" > "$URLFILE"
fi
