@echo off
cd /d "%~dp0"
echo [%date% %time%] Starting cloudflared tunnel... > .tunnel_url.txt
cloudflared tunnel --url http://localhost:8766 >> .tunnel_url.txt 2>&1
