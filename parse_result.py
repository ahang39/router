#!/usr/bin/env python3
"""解析 cfst CSV 结果，生成 edgetunnel 自定义优选格式"""

import csv
import os
import sys
from datetime import datetime

GIT_DIR = "/opt/data/hermespace/git/router"
LATEST_CSV = os.path.join(GIT_DIR, "latest.csv")
ALL_TXT = os.path.join(GIT_DIR, "all.txt")

# 地区码中文映射
REGION_MAP = {
    "NRT": "日本东京",
    "KIX": "日本大阪",
    "ICN": "韩国首尔",
    "SIN": "新加坡",
    "HKG": "中国香港",
    "TPE": "中国台湾",
    "LAX": "美国洛杉矶",
    "SJC": "美国圣何塞",
    "SEA": "美国西雅图",
    "FRA": "德国法兰克粉",
    "AMS": "荷兰阿姆斯特丹",
    "LHR": "英国伦敦",
    "CDG": "法国巴黎",
    "NRT": "日本成田",
}


def parse_csv(csv_path):
    """解析 CSV，返回格式化的行列表"""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = row["IP 地址"].strip()
            latency = row["平均延迟"].strip()
            speed = row["下载速度(MB/s)"].strip()
            region = row["地区码"].strip()
            loss = row["丢包率"].strip()

            # 跳过丢包的
            if float(loss) > 0:
                continue

            # 跳过速度低于 10MB/s 的
            if float(speed) < 10:
                continue

            region_cn = REGION_MAP.get(region, region)
            latency_int = round(float(latency))
            speed_int = round(float(speed))

            # 格式: IP:443#地区|延迟|速度
            line = f"{ip}:443#{region_cn}|{latency_int}ms|{speed_int}MB/s"
            rows.append({
                "line": line,
                "latency": float(latency),
                "speed": float(speed),
            })

    # 按速度降序排列
    rows.sort(key=lambda x: (-x["speed"], x["latency"]))
    return rows


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else LATEST_CSV

    if not os.path.exists(csv_path):
        print(f"找不到 CSV: {csv_path}", file=sys.stderr)
        print(f"先运行: python3 run_speedtest.py", file=sys.stderr)
        sys.exit(1)

    rows = parse_csv(csv_path)
    if not rows:
        print("没有可用的结果（全部丢包？）", file=sys.stderr)
        sys.exit(1)

    lines = [r["line"] for r in rows]

    with open(ALL_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[{datetime.now():%H:%M:%S}] 已生成 {ALL_TXT}")
    print(f"  共 {len(lines)} 个优选 IP")
    print(f"\n--- Top 10 ---")
    for line in lines[:10]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
