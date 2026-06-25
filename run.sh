#!/bin/bash
set -e

# 路径
SCRIPT_DIR="/opt/data/hermespace/git/router"
PYTHON="/usr/bin/python3"

# 清除代理，cfst 必须直连
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy

echo "===== [$(date '+%Y-%m-%d %H:%M:%S')] 开始多地区优选 ====="

# 1. 运行 cfst HTTPing 测速
$PYTHON "$SCRIPT_DIR/run_speedtest.py"

# 2. 解析结果，生成 all.txt
$PYTHON "$SCRIPT_DIR/parse_result.py"

# 3. git 提交推送
cd "$SCRIPT_DIR"
git add -A
git commit -m "auto: $(date '+%Y%m%d') 多地区优选更新" || echo "没有变更，跳过提交"
git push || echo "推送失败，跳过"

echo "===== [$(date '+%Y-%m-%d %H:%M:%S')] 完成 ====="
