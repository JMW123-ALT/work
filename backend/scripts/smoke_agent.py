"""Smoke test for the single-backend Wenchuang Agent flow."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--query", default="根据秀洲区郊野公园概念方案给我出一个方案")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-confidence", type=float, default=0.7)
    args = parser.parse_args()

    checks = [
        ("health", "GET", "/api/health", None),
        (
            "search",
            "POST",
            "/api/v1/search",
            {
                "query": args.query,
                "user_type": "visitor",
                "top_k": args.top_k,
                "min_confidence": 0.0,
            },
        ),
        (
            "chat",
            "POST",
            "/api/chat",
            {
                "query": args.query,
                "user_type": "visitor",
                "top_k": args.top_k,
                "min_confidence": args.min_confidence,
            },
        ),
        (
            "stream",
            "POST",
            "/api/v1/chat/stream",
            {
                "query": args.query,
                "user_type": "visitor",
                "top_k": args.top_k,
                "min_confidence": args.min_confidence,
            },
        ),
    ]

    ok = True
    for name, method, path, payload in checks:
        started = time.perf_counter()
        status, body = request(args.base_url + path, method, payload)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        summary = summarize(name, body)
        print(
            json.dumps(
                {
                    "check": name,
                    "status": status,
                    "elapsed_ms": elapsed_ms,
                    "summary": summary,
                },
                ensure_ascii=False,
            )
        )
        ok = ok and 200 <= status < 300

    return 0 if ok else 1


def request(url: str, method: str, payload: dict | None) -> tuple[int, str]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def summarize(name: str, body: str) -> dict:
    if name == "stream":
        return {
            "has_final_event": "event: final" in body,
            "has_delta_event": "event: delta" in body,
            "bytes": len(body.encode("utf-8")),
        }
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"bytes": len(body.encode("utf-8"))}
    if name == "search":
        return {"items": len(data.get("items") or [])}
    if name == "chat":
        return {
            "status": data.get("status"),
            "llm_modes": data.get("llm_modes"),
            "evidence": len(data.get("evidence") or []),
        }
    return data


if __name__ == "__main__":
    sys.exit(main())
