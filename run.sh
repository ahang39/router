#!/bin/bash
set -euo pipefail

# 与 hermes cf_speedtest.sh 同逻辑（旧机路径）。
# 1) TCPing 粗筛  2) HTTPing@公共  3) 下载@自建 Worker

SCRIPT_DIR="${CFST_GIT_DIR:-/opt/data/hermespace/git/router}"
CFST_DIR="${CFST_DIR:-/opt/data/tools/CloudflareSpeedTest}"
PYTHON="${PYTHON:-/usr/bin/python3}"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy

CFST_URL="${CFST_URL:-https://cfst.huaduo.de/url}"
CFST_HTTP_URL="${CFST_HTTP_URL:-https://speed.cloudflare.com/__down?bytes=1000000}"
CFST_CFCOLO="${CFST_CFCOLO:-}"

CFST_N="${CFST_N:-200}"
CFST_TCP_TL="${CFST_TCP_TL:-600}"
CFST_HTTP_TOP="${CFST_HTTP_TOP:-100}"
CFST_HTTP_T="${CFST_HTTP_T:-2}"
CFST_HTTP_TL="${CFST_HTTP_TL:-600}"
CFST_DN="${CFST_DN:-15}"
CFST_DT="${CFST_DT:-10}"
CFST_SL="${CFST_SL:-0}"
CFST_DL_TL="${CFST_DL_TL:-600}"

TCP_CSV="$SCRIPT_DIR/stage-tcp.csv"
HTTP_CSV="$SCRIPT_DIR/stage-http.csv"
OUT_CSV="$SCRIPT_DIR/latest.csv"
TOP_IP_FILE="$SCRIPT_DIR/stage-top.ips"

if [ ! -x "$CFST_DIR/cfst" ]; then
  echo "[error] cfst missing: $CFST_DIR/cfst" >&2
  exit 1
fi

run_cfst() {
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
    "$CFST_DIR/cfst" "$@"
}

pick_top_ips() {
  local csv="$1" max_n="$2" out="$3"
  "$PYTHON" - "$csv" "$max_n" "$out" <<'PY'
import csv, sys
from pathlib import Path

src, max_n, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
rows = []
with open(src, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        try:
            loss = float(row.get("丢包率") or "1")
            lat = float(row.get("平均延迟") or "99999")
        except ValueError:
            continue
        ip = (row.get("IP 地址") or "").strip()
        if not ip or loss > 0:
            continue
        rows.append((lat, ip))
rows.sort(key=lambda x: x[0])
ips, seen = [], set()
for _, ip in rows:
    if ip in seen:
        continue
    seen.add(ip)
    ips.append(ip)
    if len(ips) >= max_n:
        break
if not ips:
    raise SystemExit(f"no usable IPs in {src}")
out.write_text("\n".join(ips) + "\n", encoding="utf-8")
print(f"[stage] top {len(ips)} IPs -> {out}")
PY
}

ips_csv() {
  "$PYTHON" -c "print(','.join(open(r'''$1''',encoding='utf-8').read().split()))"
}

cd "$CFST_DIR"

echo "[1/3] TCPing coarse screen..."
run_cfst -n "$CFST_N" -t 4 -tl "$CFST_TCP_TL" -dd -p 0 -o "$TCP_CSV" >/dev/null

pick_top_ips "$TCP_CSV" "$CFST_HTTP_TOP" "$TOP_IP_FILE"
TOP_IP_CSV="$(ips_csv "$TOP_IP_FILE")"

echo "[2/3] HTTPing on public URL..."
HTTP_ARGS=(
  -httping -url "$CFST_HTTP_URL" -ip "$TOP_IP_CSV"
  -n "$CFST_N" -t "$CFST_HTTP_T" -tl "$CFST_HTTP_TL"
  -dd -p 0 -o "$HTTP_CSV"
)
if [ -n "$CFST_CFCOLO" ]; then
  HTTP_ARGS+=(-cfcolo "$CFST_CFCOLO")
fi
if ! run_cfst "${HTTP_ARGS[@]}" >/dev/null; then
  echo "[warn] public HTTPing failed, fallback CFST_URL"
  HTTP_ARGS=(
    -httping -url "$CFST_URL" -ip "$TOP_IP_CSV"
    -n "$CFST_N" -t "$CFST_HTTP_T" -tl "$CFST_HTTP_TL"
    -dd -p 0 -o "$HTTP_CSV"
  )
  if [ -n "$CFST_CFCOLO" ]; then
    HTTP_ARGS+=(-cfcolo "$CFST_CFCOLO")
  fi
  run_cfst "${HTTP_ARGS[@]}" >/dev/null
fi

DL_POOL=$((CFST_DN * 3))
if [ "$DL_POOL" -lt 30 ]; then DL_POOL=30; fi
if [ "$DL_POOL" -gt "$CFST_HTTP_TOP" ]; then DL_POOL="$CFST_HTTP_TOP"; fi
pick_top_ips "$HTTP_CSV" "$DL_POOL" "$TOP_IP_FILE"
TOP_IP_CSV="$(ips_csv "$TOP_IP_FILE")"

echo "[3/3] download on self-hosted worker..."
run_cfst \
  -url "$CFST_URL" -ip "$TOP_IP_CSV" \
  -n "$CFST_N" -t 1 \
  -dn "$CFST_DN" -dt "$CFST_DT" \
  -tl "$CFST_DL_TL" -sl "$CFST_SL" \
  -p 0 -o "$OUT_CSV" \
  >/dev/null

"$PYTHON" "$SCRIPT_DIR/parse_result.py" 2>&1

cd "$SCRIPT_DIR"
git add -A
git commit -m "auto: $(date '+%Y%m%d') 优选更新" >/dev/null 2>&1 || true
git push >/dev/null 2>&1 || true
