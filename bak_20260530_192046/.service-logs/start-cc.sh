#!/bin/bash
source /opt/data/home/.bashrc
echo "=== 环境变量验证 ===" >> /opt/data/luna/.service-logs/cc.log
echo "ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL" >> /opt/data/luna/.service-logs/cc.log
echo "ANTHROPIC_MODEL=$ANTHROPIC_MODEL" >> /opt/data/luna/.service-logs/cc.log
echo "TOKEN长度: ${#ANTHROPIC_AUTH_TOKEN}" >> /opt/data/luna/.service-logs/cc.log
echo "======================" >> /opt/data/luna/.service-logs/cc.log
exec /opt/data/home/npm-global/bin/cc-connect --config /opt/data/home/.cc-connect/config.toml
