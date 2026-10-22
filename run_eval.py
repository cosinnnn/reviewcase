#!/usr/bin/env python3
"""批量调用百炼模型测试接口 /test/online-web-search，跑测试集并导出结果。

只用 Python 标准库（3.8+），需在能访问内网的机器上运行。

输入：CSV（UTF-8，Excel 另存为 "CSV UTF-8" 即可），必须有 query 列，
      可选 id 列；其他列原样带到结果里（如 期望答案、分类）。
输出：CSV（utf-8-sig，Excel 直接打开不乱码），每条 query × 每个模型一行。

示例：
  python3 run_eval.py cases.csv
  python3 run_eval.py cases.csv --models qwen3.7-flash --concurrency 1
  python3 run_eval.py cases.csv --system-prompt-file prompt.txt -o out.csv
"""
import argparse
import csv
import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_URL = "http://logan-gateway.test.logan.xiaopeng.local/bolt-navigation-boot/test/online-web-search"
DEFAULT_MODELS = ["qwen-plus-character", "qwen3.7-flash"]
# 文档：连接 10 秒、读取 120 秒；urllib 只有一个超时，取二者之和
TIMEOUT_SECONDS = 130


def call(url, query, model, system_prompt):
    body = {"query": query, "model": model}
    if system_prompt:
        body["systemPrompt"] = system_prompt
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
        http_status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        http_status = e.code
    except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
        return {"http_status": "", "code": "", "resp_model": "", "latency_ms": "",
                "wall_ms": int((time.monotonic() - start) * 1000), "text": "",
                "error": f"{type(e).__name__}: {e}"}
    wall_ms = int((time.monotonic() - start) * 1000)
    try:
        data = json.loads(raw)
    except ValueError:
        return {"http_status": http_status, "code": "", "resp_model": "", "latency_ms": "",
                "wall_ms": wall_ms, "text": "", "error": f"非 JSON 响应: {raw[:200]}"}
    return {
        "http_status": http_status,
        "code": data.get("code", ""),
        "resp_model": data.get("model", ""),
        "latency_ms": data.get("latencyMs", ""),
        "wall_ms": wall_ms,
        "text": data.get("text", ""),
        "error": "",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="测试集 CSV，需含 query 列")
    p.add_argument("-o", "--output", help="结果 CSV，默认 <input>_result_<时间>.csv")
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="要跑的模型，默认两个都跑")
    p.add_argument("--concurrency", type=int, default=2, help="并发数，测试环境勿调大（默认 2）")
    p.add_argument("--interval", type=float, default=0.5, help="每个并发线程两次请求间隔秒数")
    p.add_argument("--system-prompt", help="覆盖默认 System Prompt")
    p.add_argument("--system-prompt-file", help="从文件读取 System Prompt")
    args = p.parse_args()

    system_prompt = args.system_prompt
    if args.system_prompt_file:
        with open(args.system_prompt_file, encoding="utf-8") as f:
            system_prompt = f.read()

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "query" not in (reader.fieldnames or []):
            sys.exit(f"输入文件缺少 query 列，当前列: {reader.fieldnames}")
        extra_cols = [c for c in reader.fieldnames if c not in ("id", "query")]
        cases = [r for r in reader if (r.get("query") or "").strip()]
    for i, r in enumerate(cases, 1):
        r.setdefault("id", "")
        r["id"] = r["id"] or str(i)

    output = args.output or f"{args.input.rsplit('.', 1)[0]}_result_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    fields = ["id", "query", *extra_cols, "model", "http_status", "code", "resp_model",
              "latency_ms", "wall_ms", "text", "error"]
    jobs = [(c, m) for c in cases for m in args.models]
    print(f"{len(cases)} 条 query × {len(args.models)} 个模型 = {len(jobs)} 次调用，并发 {args.concurrency}")

    lock = threading.Lock()
    stats = {"done": 0, "ok": 0}

    def run(case, model):
        result = call(args.url, case["query"], model, system_prompt)
        time.sleep(args.interval)
        return case, model, result

    # 边跑边写，中途中断也能保留已完成结果
    with open(output, "w", encoding="utf-8-sig", newline="") as out, \
            ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        futures = [pool.submit(run, c, m) for c, m in jobs]
        for fut in as_completed(futures):
            case, model, result = fut.result()
            with lock:
                writer.writerow({**case, "model": model, **result})
                out.flush()
                stats["done"] += 1
                stats["ok"] += result["code"] == 0
                flag = "OK " if result["code"] == 0 else "ERR"
                print(f"[{stats['done']}/{len(jobs)}] {flag} id={case['id']} {model} "
                      f"code={result['code']} {result['wall_ms']}ms {result['error'][:80]}")

    print(f"完成：成功 {stats['ok']}/{len(jobs)}，结果写入 {output}")


if __name__ == "__main__":
    main()
