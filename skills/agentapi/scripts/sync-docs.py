#!/usr/bin/env python3
"""从七牛开发者中心生成 AgentAPI skill 的参考资料。"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from bs4 import BeautifulSoup
from markdownify import BACKSLASH, MarkdownConverter
import yaml


SOURCE = "https://developer.qiniu.com/agentapi"
DOC_HOST = "developer.qiniu.com"
ATTACHMENT_HOST = "dn-odum9helk.qbox.me"
ARTICLE_PATH = re.compile(r"/agentapi/[0-9]+/([a-z0-9]+(?:-[a-z0-9]+)*)")
SKIP_SECTIONS = {"产品动态", "购买指南"}
NOTICE = "<!-- 由 scripts/sync-docs.py 自动生成。 -->"
SKILL_DIR = Path(__file__).resolve().parents[1]
MAX_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class Article:
    section: str
    title: str
    url: str
    filename: str


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlsplit(req.full_url), urlsplit(newurl)
        if (new.scheme, new.netloc) != (old.scheme, old.netloc):
            raise ValueError(f"拒绝跨域跳转：{req.full_url} -> {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, content_types: set[str]) -> bytes:
    request = Request(url, headers={"User-Agent": "Qiniu-AgentAPI-Skill-Docs/1.0"})
    opener = build_opener(SameOriginRedirect())
    for attempt in range(3):
        try:
            with opener.open(request, timeout=30) as response:
                if response.headers.get_content_type() not in content_types:
                    raise ValueError(f"响应类型不符：{url}")
                content = response.read(MAX_BYTES + 1)
                if not content or len(content) > MAX_BYTES:
                    raise ValueError(f"响应为空或超过 4 MiB：{url}")
                return content
        except URLError as error:
            retryable = not isinstance(error, HTTPError) or error.code in {429, 500, 502, 503, 504}
            if not retryable or attempt == 2:
                raise ValueError(f"抓取失败：{url}（{error}）") from error
            time.sleep(attempt + 1)
    raise AssertionError("retry loop must return or raise")


def html(url: str) -> str:
    return fetch(url, {"text/html"}).decode("utf-8")


def discover(index: str) -> list[Article]:
    soup = BeautifulSoup(index, "html.parser")
    articles = []
    for group in soup.select(".topic-sidebar-wrap .doctree > ul > li"):
        label = group.select_one(":scope > a.node-title")
        if label is None:
            raise ValueError("线上文档目录节点缺少标题")
        section = label.get_text(strip=True)
        if section in SKIP_SECTIONS:
            continue
        for link in group.select("li > a.node-title[href]"):
            url = urljoin(SOURCE, link["href"])
            parsed = urlsplit(url)
            match = ARTICLE_PATH.fullmatch(parsed.path)
            if not match or parsed.scheme != "https" or parsed.netloc != DOC_HOST:
                continue
            slug = match[1].removeprefix("agentapi-")
            if slug == "portal":
                continue
            title = link.get_text(strip=True)
            if not title:
                raise ValueError(f"文章标题为空：{url}")
            articles.append(Article(section, title, parsed._replace(query="", fragment="").geturl(), f"{slug}.md"))
    if not articles:
        raise ValueError("线上文档目录为空或结构变化")
    if len({article.filename for article in articles}) != len(articles):
        raise ValueError("线上目录包含重复文章文件名")
    return articles


class ArticleConverter(MarkdownConverter):
    def escape(self, text, parent_tags):
        # CMS table cells may contain literal backticks and backslashes.
        text = text.replace("\\", "\\\\").replace("`", "\\`")
        return super().escape(text, parent_tags)

    def convert_pre(self, el, text, parent_tags):
        code = el.get_text().rstrip("\n")
        classes = el.code.get("class", []) if el.code else []
        language = next((c[9:] for c in classes if re.fullmatch(r"language-[a-zA-Z0-9_+-]+", c)), "")
        fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", code)), default=0))
        return f"\n\n{fence}{language}\n{code}\n{fence}\n\n"

    def convert_td(self, el, text, parent_tags):
        text = re.sub(r"(?<!\\)\|", r"\\|", text)
        return super().convert_td(el, text, parent_tags)

    convert_th = convert_td


def convert(article: Article, document: str, local_links: dict[str, str]) -> tuple[str, str | None]:
    soup = BeautifulSoup(document, "html.parser")
    title = soup.select_one(".topic-title h1")
    bodies = soup.select(".topic-detail")
    if title is None or title.get_text(strip=True) != article.title:
        raise ValueError(f"目录与正文标题不符：{article.url}")
    if len(bodies) != 1 or not bodies[0].get_text(strip=True):
        raise ValueError(f"正文为空或结构变化：{article.url}")
    body = bodies[0]
    if body.select_one("script, style, iframe, form"):
        raise ValueError(f"正文含不支持的嵌入元素：{article.url}")

    for image in body.select("img"):
        image.decompose()
    attachment = None
    for link in body.select("a[href]"):
        if not link.get_text(strip=True):
            link.decompose()
            continue
        url = urljoin(article.url, link["href"])
        parsed = urlsplit(url)
        if parsed.scheme not in {"https", "http", "mailto"}:
            link.unwrap()
            continue
        if article.filename == "openapi.md" and link.get_text(" ", strip=True) == "下载 OpenAPI YAML":
            if attachment is not None or parsed.scheme != "https" or parsed.netloc != ATTACHMENT_HOST:
                raise ValueError(f"OpenAPI 附件链接变化：{url}")
            attachment = url
            link["href"] = "openapi.yaml"
        else:
            link["href"] = local_links.get(url, url)
    converter = ArticleConverter(heading_style="ATX", bullets="-", autolinks=False, newline_style=BACKSLASH)
    markdown = converter.convert_soup(body).strip()
    if not markdown:
        raise ValueError(f"转换后的正文为空：{article.url}")
    content = f"{NOTICE}\n\n# {article.title}\n\n原文：<{article.url}>\n\n{markdown}\n"
    return content, attachment


def load_openapi(url: str) -> bytes:
    data = fetch(url, {"application/yaml", "application/x-yaml", "text/yaml", "text/plain", "application/octet-stream"})
    spec = yaml.safe_load(data)
    paths = spec.get("paths") if isinstance(spec, dict) else None
    if not isinstance(paths, dict) or not {"/v1/agents", "/v1/sessions"}.issubset(paths):
        raise ValueError(f"OpenAPI 附件缺少 AgentAPI 端点：{url}")
    if spec.get("swagger") != "2.0" and not str(spec.get("openapi", "")).startswith("3."):
        raise ValueError(f"无法识别 OpenAPI 版本：{url}")
    return data


def render_index(articles: list[Article]) -> str:
    lines = [
        NOTICE, "", "# AgentAPI 参考资料", "", f"官方文档：<{SOURCE}>",
        "", "请求与响应结构见 [OpenAPI 附件](openapi.yaml)。", "",
    ]
    for section, group in groupby(articles, key=lambda article: article.section):
        lines.extend([f"## {section}", ""])
        for article in group:
            lines.append(f"- [{article.title}]({article.filename}) · [原文]({article.url})")
        lines.append("")
    return "\n".join(lines)


def build_references(skill_dir: Path) -> dict[str, bytes]:
    articles = discover(html(SOURCE))
    local_links = {article.url: article.filename for article in articles}
    with ThreadPoolExecutor(max_workers=5) as executor:
        documents = executor.map(html, (article.url for article in articles))
        generated = {}
        attachment = None
        for article, document in zip(articles, documents):
            markdown, found_attachment = convert(article, document, local_links)
            generated[article.filename] = markdown.encode("utf-8")
            if found_attachment:
                attachment = found_attachment
    if attachment is None:
        raise ValueError("找不到公开 OpenAPI YAML 附件")
    generated["openapi.yaml"] = load_openapi(attachment)
    generated["INDEX.md"] = render_index(articles).encode("utf-8")
    required = set(re.findall(r"\]\(references/([a-zA-Z0-9.-]+)\)", (skill_dir / "SKILL.md").read_text(encoding="utf-8")))
    if missing := required.difference(generated):
        raise ValueError("SKILL.md 引用的资料未生成：" + ", ".join(sorted(missing)))
    return generated


def sync(skill_dir: Path, check: bool) -> int:
    generated = build_references(skill_dir)
    references = skill_dir / "references"
    stale = sorted(
        path for path in references.glob("*.md")
        if path.name not in generated and path.read_bytes().startswith(NOTICE.encode("utf-8"))
    )
    changed = {}
    for name, content in sorted(generated.items()):
        path = references / name
        if not path.exists() or path.read_bytes() != content:
            changed[path] = content
    for path in changed:
        print(f"更新 {path.relative_to(skill_dir)}")
    for path in stale:
        print(f"移除 {path.relative_to(skill_dir)}")
    if check:
        return int(bool(changed or stale))
    references.mkdir(exist_ok=True)
    for path, content in changed.items():
        path.write_bytes(content)
    for path in stale:
        path.unlink()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="比较生成结果，有差异时退出 1，不修改文件")
    args = parser.parse_args()
    try:
        return sync(SKILL_DIR, args.check)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"同步失败：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
