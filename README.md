上海电信 CF 优选 IP，每日更新。

```text
https://raw.githubusercontent.com/ahang39/router/refs/heads/main/all.txt
```

测速流程（`run.sh` / hermes `cf_speedtest.sh`）：

1. **TCPing** 全量粗筛（不 HTTP）
2. **HTTPing** TopN @ 公共 URL（默认 `speed.cloudflare.com`，延迟 + 地区码）
3. **下载** Top dn @ 自建 `https://cfst.huaduo.de/url`（几乎只在这步消耗 Worker 请求）

常用环境变量：`CFST_URL`、`CFST_HTTP_URL`、`CFST_HTTP_TOP`、`CFST_DN`、`CFST_SL`。
