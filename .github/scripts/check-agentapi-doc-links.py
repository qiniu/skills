#!/usr/bin/env python3
"""Check the canonical URLs in the AgentAPI skill's documentation index."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


INDEX = Path("skills/agentapi/references/INDEX.md")
LINK = re.compile(r"\]\((https?://[^)\s]+)\)")
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def check_url(url: str) -> str | None:
    request = Request(url, headers={"User-Agent": "Qiniu-AgentAPI-Skill-Docs/1.0"})
    for attempt in range(1, 4):
        try:
            with urlopen(request, timeout=15) as response:
                if response.geturl() != url:
                    return f"redirects to {response.geturl()}"
                if response.status != 200:
                    return f"HTTP {response.status}"
                return None
        except HTTPError as error:
            message = f"HTTP {error.code}"
            error.close()
            if error.code not in RETRYABLE_STATUS:
                return message
        except (URLError, TimeoutError) as error:
            message = str(error)
        if attempt < 3:
            time.sleep(attempt)
    return message


def main(index: Path = INDEX) -> int:
    urls = {}
    for number, line in enumerate(index.read_text(encoding="utf-8").splitlines(), start=1):
        for url in LINK.findall(line):
            urls.setdefault(url, number)
    if not urls:
        print(f"{index}: no documentation URLs found")
        return 1

    failed = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        for url, error in zip(urls, executor.map(check_url, urls)):
            if error is not None:
                print(f"{index}:{urls[url]}: {url}: {error}")
                failed += 1
    print(f"Checked {len(urls)} AgentAPI documentation links. Failed: {failed}.")
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
