#!/usr/bin/env python3
"""解析 cfst CSV 结果，按地区分组生成 edgetunnel 自定义优选格式"""

import csv
import os
import sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path

GIT_DIR = os.environ.get("CFST_GIT_DIR") or str(Path.home() / "dev/repos/router")
LATEST_CSV = os.path.join(GIT_DIR, "latest.csv")
ALL_TXT = os.path.join(GIT_DIR, "all.txt")

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

# 优先亚太多出口；欧/美作回退（电信路径常先落到 AMS 等）
TARGET_REGIONS = [
    "NRT",
    "KIX",
    "HKG",
    "SIN",
    "ICN",
    "SJC",
    "LAX",
    "SEA",
    "AMS",
    "FRA",
]

MIN_SPEED = 0
MIN_PER_REGION = 3
# 目标地区都空时，按速度取全局 Top（避免 all.txt 断更）
FALLBACK_GLOBAL_TOP = 10


def parse_csv(csv_path):
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


def _format_line(item):
    region_cn = REGION_MAP.get(item["region"], item["region"])
    latency_int = round(item["latency"])
    speed_int = round(item["speed"])
    return f"{item['ip']}:443#{region_cn}|{latency_int}ms|{speed_int}MB/s"


def select_top(regions_data):
    result_lines = []
    for region_code in TARGET_REGIONS:
        items = regions_data.get(region_code, [])
        if not items:
            continue
        items.sort(key=lambda x: -x["speed"])
        filtered = [x for x in items if x["latency"] <= 200 and x["speed"] >= MIN_SPEED]
        if len(filtered) < MIN_PER_REGION:
            relaxed = [x for x in items if x["latency"] <= 200]
            seen = {x["ip"] for x in filtered}
            for x in relaxed:
                if x["ip"] not in seen:
                    filtered.append(x)
                    seen.add(x["ip"])
        selected = filtered[:MIN_PER_REGION]
        for item in selected:
            result_lines.append(_format_line(item))

    if result_lines:
        return result_lines

    # 无目标地区命中：全局按速度取 Top，保证 all.txt 有可用结果
    all_items = []
    for items in regions_data.values():
        all_items.extend(items)
    all_items = [x for x in all_items if x["latency"] <= 600 and x["speed"] >= MIN_SPEED]
    all_items.sort(key=lambda x: -x["speed"])
    for item in all_items[:FALLBACK_GLOBAL_TOP]:
        result_lines.append(_format_line(item))
    return result_lines


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else LATEST_CSV
    if not os.path.exists(csv_path):
        print(f"找不到 CSV: {csv_path}", file=sys.stderr)
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
    region_counts = defaultdict(int)
    for line in lines:
        region_cn = line.split("#")[1].split("|")[0]
        region_counts[region_cn] += 1
    print(f"  地区分布: {dict(region_counts)}")
    print("\n--- 全部结果 ---")
    for line in lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
