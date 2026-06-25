#!/usr/bin/env python3
"""运行 CloudflareSpeedTest 多地区优选（HTTPing模式，获取地区码）"""

import subprocess
import sys
import os
from datetime import datetime

CFST_DIR = "/opt/data/tools/CloudflareSpeedTest"
OUTPUT_DIR = "/opt/data/hermespace/git/router"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(OUTPUT_DIR, f"result_{timestamp}.csv")

    cmd = [
        os.path.join(CFST_DIR, "cfst"),
        "-httping",         # HTTPing模式，获取地区码
        "-n", "50",         # 并发50，NAS友好
        "-dn", "10",        # 下载测速10个
        "-dt", "10",        # 下载测速10秒
        "-tl", "200",       # 延迟上限200ms
        "-p", "0",          # 不打印到终端
        "-o", csv_path,
    ]

    # 清除代理环境变量，必须直连
    env = {k: v for k, v in os.environ.items()
           if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}

    print(f"[{datetime.now():%H:%M:%S}] 开始多地区优选 (HTTPing模式)...")
    print(f"  并发: 50 | 下载数: 10 | 下载时间: 10s | 延迟上限: 200ms")
    print(f"  输出: {csv_path}")

    result = subprocess.run(cmd, env=env, cwd=CFST_DIR)

    if result.returncode != 0:
        print(f"cfst 退出码: {result.returncode}", file=sys.stderr)
        sys.exit(1)

    # 同时复制一份为 latest.csv
    latest_path = os.path.join(OUTPUT_DIR, "latest.csv")
    subprocess.run(["cp", csv_path, latest_path])

    print(f"\n[{datetime.now():%H:%M:%S}] 完成!")
    print(f"  历史结果: {csv_path}")
    print(f"  最新结果: {latest_path}")

if __name__ == "__main__":
    main()
