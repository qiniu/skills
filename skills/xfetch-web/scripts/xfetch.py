#!/usr/bin/env python3
import argparse
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


ACCEPT = {
    "markdown": "text/markdown",
    "json": "application/json",
    "html": "text/html",
}
TRANSIENT_STATUS = {429, 502, 503, 504}


def build_fetch_url(base_url: str, target_url: str) -> str:
    target = urllib.parse.urlsplit(target_url)
    if target.scheme not in ("http", "https") or not target.netloc:
        raise SystemExit("target URL must be absolute http or https")
    base = base_url.rstrip("/")
    path = urllib.parse.quote(target.path or "/", safe="/%:@!$&()*+,;=~-._")
    fetch_url = f"{base}/{target.scheme}/{target.netloc}{path}"
    if target.query:
        fetch_url += "?" + target.query
    return fetch_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a URL through Qiniu xfetch.")
    parser.add_argument("url")
    parser.add_argument("--format", choices=sorted(ACCEPT), default="markdown")
    parser.add_argument("--base-url", default=os.environ.get("XFETCH_BASE_URL", "https://xfetch.qiniuapi.com"))
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()

    req = urllib.request.Request(
        build_fetch_url(args.base_url, args.url),
        headers={"Accept": ACCEPT[args.format]},
        method="GET",
    )
    token = os.environ.get("XFETCH_API_KEY", "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    attempts = max(1, args.retries + 1)
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                sys.stdout.buffer.write(resp.read())
            return 0
        except urllib.error.HTTPError as err:
            detail = err.read(4096).decode("utf-8", "replace")
            if err.code not in TRANSIENT_STATUS or attempt == attempts - 1:
                sys.stderr.write(f"xfetch HTTP {err.code}: {detail}\n")
                return 1
        except Exception as err:
            if attempt == attempts - 1:
                sys.stderr.write(f"xfetch failed: {err}\n")
                return 1
        time.sleep(0.5 * (attempt + 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
