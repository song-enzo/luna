#!/usr/bin/env bash
# ============================================================
# LUNA 服务启动脚本（独立于小天容器）
# 用 setsid 启动，脱离父进程树，重启容器也不受影响
# ============================================================
set -e

BASEDIR="/opt/data/luna"
LOGDIR="/tmp/luna-services"
mkdir -p "$LOGDIR"

# 加载环境变量（Claude Code → DeepSeek）
source /opt/data/home/.bashrc
export PATH="/opt/data/home/npm-global/bin:$PATH"

log() {
  echo "[$(date '+%H:%M:%S')] $1" >> "$LOGDIR/startup.log"
}

log "=== 启动 LUNA 服务 ==="

# 1. LUNA Flask 网站（端口 8766）
log "启动 Flask..."
setsid /opt/data/luna/.venv/bin/python /opt/data/luna/luna_app.py \
  >> "$LOGDIR/flask.log" 2>&1 &
FLASK_PID=$!
log "  Flask PID: $FLASK_PID"

sleep 2

# 2. cc-connect（程哥 Telegram Bot）
log "启动 cc-connect..."
setsid cc-connect --config /opt/data/home/.cc-connect/config.toml \
  >> "$LOGDIR/cc-connect.log" 2>&1 &
CC_PID=$!
log "  cc-connect PID: $CC_PID"

sleep 2

# 3. code-server（程哥工作台，端口 8081）
log "启动 code-server..."
setsid /opt/data/code-server/bin/code-server --bind-addr 0.0.0.0:8081 /opt/data/luna \
  >> "$LOGDIR/code-server.log" 2>&1 &
CS_PID=$!
log "  code-server PID: $CS_PID"

sleep 2

# 4. Cloudflare 隧道：LUNA 网站（端口 8766）
log "启动 LUNA 隧道..."
setsid npx cloudflared tunnel --url http://localhost:8766 \
  >> "$LOGDIR/tunnel-luna.log" 2>&1 &
TL_PID=$!
log "  LUNA隧道 PID: $TL_PID"

# 5. Cloudflare 隧道：code-server（端口 8081）
log "启动 code-server 隧道..."
setsid npx cloudflared tunnel --url http://localhost:8081 \
  >> "$LOGDIR/tunnel-codeserver.log" 2>&1 &
TC_PID=$!
log "  code-server隧道 PID: $TC_PID"

sleep 5

# 输出隧道 URL
LUNA_URL=$(grep -o 'https://[a-z-]*\.trycloudflare\.com' "$LOGDIR/tunnel-luna.log" 2>/dev/null | sort -u | head -1)
CS_URL=$(grep -o 'https://[a-z-]*\.trycloudflare\.com' "$LOGDIR/tunnel-codeserver.log" 2>/dev/null | sort -u | head -1)

log ""
log "====== 服务状态 ======"
log "🌐 LUNA 网站:  $LUNA_URL"
log "🤖 程哥 Bot:   @xiaocheng26526_bot"
log "🖥️ 程哥工作台: $CS_URL（密码 luna2025）"
log "======================"
