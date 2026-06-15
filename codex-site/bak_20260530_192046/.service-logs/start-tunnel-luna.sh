#!/bin/bash
# 启动 LUNA 网站 Cloudflare 隧道，禁用自动更新防止 URL 漂移
CLOUDFLARED=/opt/data/home/.npm/_npx/8a26fc3a61fe4212/node_modules/cloudflared/bin/cloudflared
LOGFILE=/opt/data/luna/.service-logs/tunnel-luna.log
URLFILE=/nas/hermes/小天专用/助理/luna-url.txt

# --no-autoupdate 防止自动更新导致隧道重启、URL 改变
"$CLOUDFLARED" tunnel --no-autoupdate --url http://localhost:8766 > "$LOGFILE" 2>&1 &

# 等待 URL 分配，写入固定位置
sleep 8
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGFILE" 2>/dev/null | tail -1)
if [ -n "$URL" ]; then
  echo "$URL" > "$URLFILE"
fi
