#!/bin/bash
# LUNA 服务管理脚本
# 用法: sh /opt/data/luna/luna-service.sh start|stop|restart|status
# 日志目录
LOGDIR=/opt/data/luna/.service-logs
PIDFILE=$LOGDIR/pids
LUNA_DIR=/opt/data/luna

mkdir -p $LOGDIR

# 获取云隧道 URL
get_tunnel_url() {
    local port=$1
    local logfile=$2
    if [ -f "$logfile" ]; then
        grep -o 'https://[a-z-]*\.trycloudflare\.com' "$logfile" 2>/dev/null | tail -1
    fi
}

status() {
    echo "=== LUNA 服务状态 ==="
    local flask_pid cc_pid cs_pid
    
    [ -f $PIDFILE ] && . $PIDFILE 2>/dev/null
    
    # 检查 Flask
    if [ -n "$FLASK_PID" ] && kill -0 $FLASK_PID 2>/dev/null; then
        echo "  🌐 网站 (Flask)  PID=$FLASK_PID ✅ 运行中"
    else
        echo "  🌐 网站 (Flask)  ❌ 未运行"
    fi
    
    # 检查 cc-connect
    if [ -n "$CC_PID" ] && kill -0 $CC_PID 2>/dev/null; then
        echo "  🤖 程哥 Bot     PID=$CC_PID ✅ 运行中"
    else
        echo "  🤖 程哥 Bot     ❌ 未运行"
    fi
    
    # 检查 code-server
    if [ -n "$CS_PID" ] && kill -0 $CS_PID 2>/dev/null; then
        echo "  🖥️ code-server   PID=$CS_PID ✅ 运行中"
    else
        echo "  🖥️ code-server   ❌ 未运行"
    fi
    
    # 隧道地址
    local luna_url=$(get_tunnel_url 8766 "$LOGDIR/tunnel-luna.log")
    local cs_url=$(get_tunnel_url 8081 "$LOGDIR/tunnel-cs.log")
    [ -n "$luna_url" ] && echo "  🌐 网站地址: $luna_url"
    [ -n "$cs_url" ] && echo "  🖥️ 工作台地址: $cs_url"
    echo ""
}

stop() {
    echo "=== 停止 LUNA 服务 ==="
    [ -f $PIDFILE ] && . $PIDFILE 2>/dev/null
    
    # 停止 Flask
    if [ -n "$FLASK_PID" ] && kill -0 $FLASK_PID 2>/dev/null; then
        kill $FLASK_PID 2>/dev/null
        echo "  🌐 Flask 已停止"
    fi
    
    # 停止 cc-connect
    if [ -n "$CC_PID" ] && kill -0 $CC_PID 2>/dev/null; then
        kill $CC_PID 2>/dev/null
        echo "  🤖 程哥 Bot 已停止"
    fi
    
    # 停止 code-server
    if [ -n "$CS_PID" ] && kill -0 $CS_PID 2>/dev/null; then
        kill $CS_PID 2>/dev/null
        echo "  🖥️ code-server 已停止"
    fi
    
    # 清理所有 cloudflared
    pkill -f "cloudflared tunnel.*localhost" 2>/dev/null
    echo "  📡 隧道已停止"
    
    # 清理孤儿进程
    fuser -k 8766/tcp 2>/dev/null
    fuser -k 8081/tcp 2>/dev/null
    
    rm -f $PIDFILE
    echo "✅ 全部停止"
}

start() {
    echo "=== 启动 LUNA 服务 ==="
    
    # 1. Flask 网站
    cd $LUNA_DIR
    nohup $LUNA_DIR/.venv/bin/python $LUNA_DIR/luna_app.py \
        > $LOGDIR/flask.log 2>&1 &
    echo "FLASK_PID=$!" >> $PIDFILE
    echo "  🌐 Flask 启动中... PID=$!"
    
    sleep 2
    
    # 2. cc-connect 程哥 Bot
    nohup /opt/data/home/npm-global/bin/cc-connect \
        --config /opt/data/home/.cc-connect/config.toml \
        > $LOGDIR/cc.log 2>&1 &
    echo "CC_PID=$!" >> $PIDFILE
    echo "  🤖 程哥 Bot 启动中... PID=$!"
    
    sleep 3
    
    # 3. code-server
    nohup /opt/data/code-server/bin/code-server \
        --bind-addr 0.0.0.0:8081 /opt/data/luna \
        > $LOGDIR/code-server.log 2>&1 &
    echo "CS_PID=$!" >> $PIDFILE
    echo "  🖥️ code-server 启动中... PID=$!"
    
    sleep 3
    
    # 4. cloudflared 隧道 - LUNA 网站
    nohup npx cloudflared tunnel --url http://localhost:8766 \
        > $LOGDIR/tunnel-luna.log 2>&1 &
    echo "  📡 LUNA 隧道启动中..."
    
    sleep 1
    
    # 5. cloudflared 隧道 - code-server
    nohup npx cloudflared tunnel --url http://localhost:8081 \
        > $LOGDIR/tunnel-cs.log 2>&1 &
    echo "  📡 code-server 隧道启动中..."
    
    # 等隧道分配 URL
    echo "  ⏳ 等待隧道分配地址..."
    sleep 8
    
    local luna_url=$(get_tunnel_url 8766 "$LOGDIR/tunnel-luna.log")
    local cs_url=$(get_tunnel_url 8081 "$LOGDIR/tunnel-cs.log")
    
    echo ""
    echo "===== LUNA 服务已启动 ====="
    [ -n "$luna_url" ] && echo "🌐 网站:  $luna_url" || echo "🌐 网站:  等待隧道... 稍后查看 $LOGDIR/tunnel-luna.log"
    echo "🤖 程哥:  @xiaocheng26526_bot (Telegram)"
    [ -n "$cs_url" ] && echo "🖥️ 工作台: $cs_url" || echo "🖥️ 工作台: 等待隧道... 稍后查看 $LOGDIR/tunnel-cs.log"
    echo "=========================="
}

case "${1:-status}" in
    start)
        stop 2>/dev/null  # 先停旧的
        sleep 1
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    *)
        echo "用法: sh $0 start|stop|restart|status"
        exit 1
        ;;
esac
