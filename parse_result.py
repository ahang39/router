#!/usr/bin/env python3
"""解析 cfst CSV 结果，按地区分组生成 edgetunnel 自定义优选格式"""

import csv
import os
import sys
from datetime import datetime
from collections import defaultdict

GIT_DIR = "/opt/data/hermespace/git/router"
LATEST_CSV = os.path.join(GIT_DIR, "latest.csv")
ALL_TXT = os.path.join(GIT_DIR, "all.txt")

# 地区码中文映射
REGION_MAP = {
    "NRT": "日本成田",
    "KIX": "日本大阪",
    "HND": "日本东京",
    "ICN": "韩国首尔",
    "SIN": "新加坡",
    "HKG": "中国香港",
    "KHH": "中国高雄",
    "TPE": "中国台湾台北",
    "LAX": "美国洛杉矶",
    "SJC": "美国圣何塞",
    "SEA": "美国西雅图",
    "FRA": "德国法兰克福",
    "AMS": "荷兰阿姆斯特丹",
    "LHR": "英国伦敦",
    "CDG": "法国巴黎",
    "MAD": "西班牙马德里",
}

# 目标地区（优先级从高到低）
TARGET_REGIONS = ["NRT", "KIX", "HKG", "SIN", "ICN", "SJC", "LAX", "SEA"]

MIN_SPEED = 0       # 不限速度
MIN_PER_REGION = 3  # 每个地区至少保留数量


def parse_csv(csv_path):
    """解析 CSV，返回按地区分组的数据"""
    regions = defaultdict(list)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = row["IP 地址"].strip()
            latency = row["平均延迟"].strip()
            speed = row["下载速度(MB/s)"].strip()
            region = row["地区码"].strip()
            loss = row["丢包率"].strip()

            if float(loss) > 0:
                continue

            regions[region].append({
                "ip": ip,
                "latency": float(latency),
                "speed": float(speed),
                "region": region,
            })

    return regions


def select_top(regions_data):
    """每个地区筛选：先过滤延迟≤200+速度≥5，按速度排序，至少保留MIN_PER_REGION个"""
    result_lines = []

    for region_code in TARGET_REGIONS:
        items = regions_data.get(region_code, [])
        if not items:
            continue

        # 先按速度降序排
        items.sort(key=lambda x: -x["speed"])

        # 过滤：延迟≤200 且 速度≥5
        filtered = [x for x in items if x["latency"] <= 200 and x["speed"] >= MIN_SPEED]

        # 如果不足 MIN_PER_REGION，放宽速度限制（只保留延迟≤200的）
        if len(filtered) < MIN_PER_REGION:
            relaxed = [x for x in items if x["latency"] <= 200]
            # 合并去重
            seen = {x["ip"] for x in filtered}
            for x in relaxed:
                if x["ip"] not in seen:
                    filtered.append(x)
                    seen.add(x["ip"])

        # 取 top MIN_PER_REGION（或全部，如果不够）
        selected = filtered[:MIN_PER_REGION]

        region_cn = REGION_MAP.get(region_code, region_code)
        for item in selected:
            latency_int = round(item["latency"])
            speed_int = round(item["speed"])
            line = f"{item['ip']}:443#{region_cn}|{latency_int}ms|{speed_int}MB/s"
            result_lines.append(line)

    return result_lines


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else LATEST_CSV

    if not os.path.exists(csv_path):
        print(f"找不到 CSV: {csv_path}", file=sys.stderr)
        print(f"先运行: python3 run_speedtest.py", file=sys.stderr)
        sys.exit(1)

    regions_data = parse_csv(csv_path)
    if not regions_data:
        print("没有可用的结果（全部丢包？）", file=sys.stderr)
        sys.exit(1)

    lines = select_top(regions_data)
    if not lines:
        print("没有符合条件的 IP", file=sys.stderr)
        sys.exit(1)

    with open(ALL_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[{datetime.now():%H:%M:%S}] 已生成 {ALL_TXT}")
    print(f"  共 {len(lines)} 个优选 IP")

    # 统计各地区数量
    region_counts = defaultdict(int)
    for line in lines:
        region_cn = line.split("#")[1].split("|")[0]
        region_counts[region_cn] += 1
    print(f"  地区分布: {dict(region_counts)}")

    print(f"\n--- 全部结果 ---")
    for line in lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
