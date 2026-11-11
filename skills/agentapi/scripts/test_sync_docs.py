from contextlib import redirect_stdout
from importlib import import_module
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sync_docs = import_module("sync-docs")

INDEX = """
<div class="topic-sidebar-wrap"><div class="doctree"><ul>
  <li><a class="node-title">产品动态</a><ol>
    <li><a class="node-title" href="/agentapi/123/launch">发布</a></li>
  </ol></li>
  <li><a class="node-title">购买指南</a><ol>
    <li><a class="node-title" href="/agentapi/456/billing">计费</a></li>
  </ol></li>
  <li><a class="node-title">快速入门</a><ol>
    <li><a class="node-title" href="/agentapi/13585/agentapi-access">接入准备</a></li>
    <li><a class="node-title" href="/agentapi/13586/agentapi-portal">在 Portal 中构建</a></li>
    <li><a class="node-title" href="/agentapi/13587/agentapi-quickstart">通过 API 构建</a></li>
  </ol></li>
  <li><a class="node-title">API 文档</a><ol>
    <li><a class="node-title" href="/agentapi/13619/agentapi-openapi">OpenAPI 规范</a></li>
  </ol></li>
</ul></div></div>
"""
ACCESS_URL = "https://developer.qiniu.com/agentapi/13585/agentapi-access"
PORTAL_URL = "https://developer.qiniu.com/agentapi/13586/agentapi-portal"
QUICKSTART_URL = "https://developer.qiniu.com/agentapi/13587/agentapi-quickstart"
OPENAPI_URL = "https://developer.qiniu.com/agentapi/13619/agentapi-openapi"
ATTACHMENT = "https://dn-odum9helk.qbox.me/example"
SCHEMA = b'swagger: "2.0"\npaths:\n  /v1/agents: {}\n  /v1/sessions: {}\n'


def article(title, content):
    return f'<div class="topic-title"><h1>{title}</h1></div><div class="topic-detail">{content}</div>'


def fixture_pages():
    return {
        sync_docs.SOURCE: INDEX,
        ACCESS_URL: article("接入准备", '<p>参见<a href="/agentapi/13587/agentapi-quickstart">快速入门</a>。</p>'),
        PORTAL_URL: article("在 Portal 中构建", "<p>配置并测试智能体。</p>"),
        QUICKSTART_URL: article("通过 API 构建", "<p>运行任务。</p>"),
        OPENAPI_URL: article("OpenAPI 规范", f'<p><a href="{ATTACHMENT}">下载 OpenAPI YAML</a></p>'),
    }


class SyncDocsTest(unittest.TestCase):
    def test_only_discovers_relevant_agentapi_articles(self):
        pages = sync_docs.discover(INDEX)
        self.assertEqual(
            [page.filename for page in pages], ["access.md", "portal.md", "quickstart.md", "openapi.md"]
        )

    def test_article_preserves_code_and_keeps_online_anchors(self):
        page = sync_docs.Article("快速入门", "接入准备", ACCESS_URL, "access.md")
        source = article("接入准备", """
<p><a href="/agentapi/13587/agentapi-quickstart">快速入门</a>
<a href="#details">细节</a><img src="example.png"></p>
<table><tr><th>字段</th></tr><tr><td>`base_url`</td></tr></table>
<pre><code class="language-bash">echo '$HOME &amp;&amp; ```'
printf '%s\n' "$BASE_URL"
</code></pre>
""")
        markdown, attachment = sync_docs.convert(page, source, {QUICKSTART_URL: "quickstart.md"})
        self.assertIsNone(attachment)
        self.assertIn("[快速入门](quickstart.md)", markdown)
        self.assertIn(f"[细节]({ACCESS_URL}#details)", markdown)
        self.assertNotIn("example.png", markdown)
        self.assertIn(r"| \`base\_url\` |", markdown)
        self.assertIn("````bash\necho '$HOME && ```'\nprintf '%s\n' \"$BASE_URL\"\n````", markdown)

    def test_check_is_read_only_and_successful_sync_replaces_generated_files(self):
        pages = fixture_pages()
        with TemporaryDirectory() as directory, patch.object(sync_docs, "html", side_effect=pages.__getitem__), \
                patch.object(sync_docs, "fetch", return_value=SCHEMA) as fetch, redirect_stdout(io.StringIO()):
            root = Path(directory)
            (root / "SKILL.md").write_text("[在 Portal 中构建](references/portal.md)\n", encoding="utf-8")
            references = root / "references"
            references.mkdir()
            stale = references / "stale.md"
            stale.write_text(sync_docs.NOTICE + "\n", encoding="utf-8")
            handwritten = references / "handwritten.md"
            handwritten.write_text("手写资料\n", encoding="utf-8")
            self.assertEqual(sync_docs.sync(root, check=True), 1)
            self.assertEqual(sorted(path.name for path in references.iterdir()), ["handwritten.md", "stale.md"])
            self.assertEqual(sync_docs.sync(root, check=False), 0)
            self.assertEqual(sync_docs.sync(root, check=True), 0)
            self.assertFalse(stale.exists())
            self.assertTrue(handwritten.exists())
            self.assertIn("[快速入门](quickstart.md)", (references / "access.md").read_text(encoding="utf-8"))
            self.assertIn("配置并测试智能体。", (references / "portal.md").read_text(encoding="utf-8"))
            self.assertIn("[在 Portal 中构建](portal.md)", (references / "INDEX.md").read_text(encoding="utf-8"))
            self.assertIn("[下载 OpenAPI YAML](openapi.yaml)", (references / "openapi.md").read_text(encoding="utf-8"))
            self.assertEqual((references / "openapi.yaml").read_bytes(), SCHEMA)
            self.assertEqual(fetch.call_args.args[0], ATTACHMENT)

    def test_failed_source_conversion_preserves_previous_references(self):
        pages = fixture_pages()
        pages[QUICKSTART_URL] = article("通过 API 构建", "")
        with TemporaryDirectory() as directory, patch.object(sync_docs, "html", side_effect=pages.__getitem__):
            root = Path(directory)
            references = root / "references"
            references.mkdir()
            old = references / "access.md"
            old.write_bytes(b"previous")
            with self.assertRaisesRegex(ValueError, "正文为空或结构变化"):
                sync_docs.sync(root, check=False)
            self.assertEqual(list(references.iterdir()), [old])
            self.assertEqual(old.read_bytes(), b"previous")


if __name__ == "__main__":
    unittest.main()
