#!/bin/bash
set -e

SCRIPT_DIR="/opt/data/hermespace/git/router"
PYTHON="/usr/bin/python3"

# 清除代理，cfst 必须直连
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy

# 1. 运行 cfst（静默，只输出最终结果）
cd /opt/data/tools/CloudflareSpeedTest
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
  ./cfst -httping -n 100 -dn 20 -dt 10 -tl 600 -sl 0 -p 0 -o "$SCRIPT_DIR/latest.csv" > /dev/null 2>&1

# 2. 解析结果，生成 all.txt
$PYTHON "$SCRIPT_DIR/parse_result.py" 2>&1

# 3. git 提交推送
cd "$SCRIPT_DIR"
git add -A
git commit -m "auto: $(date '+%Y%m%d') 优选更新" > /dev/null 2>&1 || true
git push > /dev/null 2>&1 || true
