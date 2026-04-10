#!/usr/bin/env python3
"""AppMarket CLI — 应用市场开发者命令行工具（零第三方依赖）。

用法:
    appmarket-cli.py create-app       --name NAME --desc DESC [--type TYPE]
    appmarket-cli.py update-app       --app-id ID [--name NAME] [--desc DESC]
    appmarket-cli.py create-version   --app-id ID [--version VER] --deploy-meta FILE
    appmarket-cli.py update-version   --app-id ID --version VER --deploy-meta FILE --desc DESC
    appmarket-cli.py test-version     --app-id ID --version VER [--inputs FILE] [--region REGION] [--cleanup]
    appmarket-cli.py publish-version  --app-id ID --version VER [--yes]
    appmarket-cli.py get-app          --app-id ID
    appmarket-cli.py get-version      --app-id ID --version VER
    appmarket-cli.py list-apps
    appmarket-cli.py list-versions    --app-id ID
    appmarket-cli.py get-instance     --app-id ID --instance-id ID
    appmarket-cli.py delete-instance  --app-id ID --instance-id ID
    appmarket-cli.py list-instances    [--app-id ID]

环境变量:
    QINIU_ACCESS_KEY   七牛 AccessKey（必需）
    QINIU_SECRET_KEY   七牛 SecretKey（必需）
    APPMARKET_API_BASE API 基地址（可选，默认 https://ecs.qiniuapi.com）
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import ssl
import sys
import time
import uuid
import urllib.error
import urllib.request
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Qiniu 签名
# ---------------------------------------------------------------------------

def qiniu_sign(access_key: str, secret_key: str, method: str, url: str,
               content_type: str = "", body: str = "") -> str:
    """生成 Qiniu 签名 Authorization header 值。

    签名算法（与 Go 实现 test/lib/auth/qiniu.go 一致）:
      string_to_sign = "<METHOD> <path>[?<query>]\\nHost: <host>\\nContent-Type: <ct>\\n\\n[<body>]"
      signature = urlsafe_base64(hmac_sha1(secret_key, string_to_sign))
      authorization = "Qiniu <access_key>:<signature>"
    """
    parsed = urlparse(url)

    host = parsed.hostname or ""
    if parsed.port and parsed.port not in (80, 443):
        host = f"{parsed.hostname}:{parsed.port}"

    data = f"{method} {parsed.path}"
    if parsed.query:
        data += f"?{parsed.query}"
    data += f"\nHost: {host}"
    if content_type:
        data += f"\nContent-Type: {content_type}"
    data += "\n\n"

    if body and content_type and content_type != "application/octet-stream":
        data += body

    h = hmac.new(secret_key.encode(), data.encode(), hashlib.sha1)
    signature = base64.urlsafe_b64encode(h.digest()).decode()
    return f"Qiniu {access_key}:{signature}"


# ---------------------------------------------------------------------------
# HTTP 客户端（标准库实现）
# ---------------------------------------------------------------------------

class _Response:
    """urllib 响应的简单封装。"""

    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.body = body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> dict:
        return json.loads(self.body)


def _http_request(method: str, url: str, headers: dict, body_bytes: bytes | None = None) -> _Response:
    """使用 urllib 发送 HTTP 请求。"""
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return _Response(resp.status, resp.read())
    except urllib.error.HTTPError as e:
        return _Response(e.code, e.read())


# ---------------------------------------------------------------------------
# AppMarket API 客户端
# ---------------------------------------------------------------------------

class AppMarketClient:
    """AppMarket API 客户端。"""

    def __init__(self, access_key: str, secret_key: str, api_base: str):
        self.ak = access_key
        self.sk = secret_key
        self.api_base = api_base.rstrip("/")

    def _request(self, method: str, path: str, json_body=None, base_override: str = "") -> _Response:
        base = base_override.rstrip("/") if base_override else self.api_base
        url = f"{base}{path}"
        body_str = ""
        body_bytes = None
        content_type = ""

        if json_body is not None:
            body_str = json.dumps(json_body, ensure_ascii=False, separators=(",", ":"))
            body_bytes = body_str.encode("utf-8")
            content_type = "application/json"

        auth = qiniu_sign(self.ak, self.sk, method, url, content_type, body_str)

        headers = {"Authorization": auth}
        if content_type:
            headers["Content-Type"] = content_type

        return _http_request(method, url, headers, body_bytes)

    def _check(self, resp: _Response, expected_codes: tuple[int, ...] = (200,)):
        if resp.status_code not in expected_codes:
            print(f"请求失败 [{resp.status_code}]", file=sys.stderr)
            try:
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False), file=sys.stderr)
            except Exception:
                print(resp.text, file=sys.stderr)
            sys.exit(1)
        if resp.status_code == 204 or not resp.body:
            return {}
        return resp.json()

    # ---- App ----

    def create_app(self, name: str, description: str, app_type: str = "Private"):
        resp = self._request("POST", "/v1/apps/", json_body={
            "name": name, "description": description, "type": app_type,
        })
        return self._check(resp)

    def get_app(self, app_id: str):
        return self._check(self._request("GET", f"/v1/apps/{app_id}"))

    def patch_app(self, app_id: str, name: str = "", description: str = ""):
        body = {}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        resp = self._request("PATCH", f"/v1/apps/{app_id}", json_body=body)
        return self._check(resp, expected_codes=(200, 204))

    def list_apps(self):
        items = []
        marker = ""
        while True:
            path = "/v1/apps/"
            if marker:
                path += f"?marker={marker}"
            resp = self._check(self._request("GET", path))
            batch = resp if isinstance(resp, list) else resp.get("items", resp.get("data", []))
            items.extend(batch)
            marker = resp.get("nextMarker", "") if isinstance(resp, dict) else ""
            if not marker:
                break
        return {"items": items}

    # ---- Version ----

    def create_version(self, app_id: str, version: str, description: str, deploy_meta: dict):
        resp = self._request("POST", f"/v1/apps/{app_id}/versions/", json_body={
            "version": version, "description": description, "deployMeta": deploy_meta,
        })
        return self._check(resp)

    def update_version(self, app_id: str, version: str, deploy_meta: dict, description: str | None = None):
        body: dict = {"deployMeta": deploy_meta}
        if description:
            body["description"] = description
        return self._check(self._request("PUT", f"/v1/apps/{app_id}/versions/{version}", json_body=body))

    def get_version(self, app_id: str, version: str):
        return self._check(self._request("GET", f"/v1/apps/{app_id}/versions/{version}"))

    def list_versions(self, app_id: str):
        items = []
        marker = ""
        while True:
            path = f"/v1/apps/{app_id}/versions/"
            if marker:
                path += f"?marker={marker}"
            resp = self._check(self._request("GET", path))
            batch = resp if isinstance(resp, list) else resp.get("items", resp.get("data", []))
            items.extend(batch)
            marker = resp.get("nextMarker", "") if isinstance(resp, dict) else ""
            if not marker:
                break
        return {"items": items}

    def publish_version(self, app_id: str, version: str):
        return self._check(
            self._request("POST", f"/v1/apps/{app_id}/versions/{version}/publish"),
            expected_codes=(200, 204),
        )

    # ---- Instance ----

    def _region_base(self, region_id: str) -> str:
        """构造 region-specific API base（如 https://ap-northeast-1-ecs.qiniuapi.com）"""
        from urllib.parse import urlparse
        parsed = urlparse(self.api_base)
        return f"{parsed.scheme}://{region_id}-{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")

    def create_instance(self, app_id: str, version: str, inputs: dict, region_id: str, input_preset_name: str = "starter"):
        resp = self._request("POST", "/v1/app-instances/", json_body={
            "appID": app_id, "appVersion": version, "inputs": inputs,
            "inputPresetName": input_preset_name, "clientToken": str(uuid.uuid4()),
        }, base_override=self._region_base(region_id))
        return self._check(resp)

    def get_instance(self, app_id: str, instance_id: str, region_id: str = ""):
        base = self._region_base(region_id) if region_id else ""
        return self._check(self._request("GET", f"/v1/app-instances/{instance_id}", base_override=base))

    def delete_instance(self, app_id: str, instance_id: str, region_id: str = ""):
        base = self._region_base(region_id) if region_id else ""
        return self._check(
            self._request("DELETE", f"/v1/app-instances/{instance_id}", base_override=base),
            expected_codes=(200, 202, 204),
        )

    def list_instances(self, app_id: str = "", region_id: str = ""):
        base = self._region_base(region_id) if region_id else ""
        items = []
        marker = ""
        while True:
            path = "/v1/app-instances/"
            params = []
            if app_id:
                params.append(f"appID={app_id}")
            if marker:
                params.append(f"marker={marker}")
            if params:
                path += "?" + "&".join(params)
            resp = self._check(self._request("GET", path, base_override=base))
            batch = resp if isinstance(resp, list) else resp.get("items", resp.get("data", []))
            items.extend(batch)
            marker = resp.get("nextMarker", "") if isinstance(resp, dict) else ""
            if not marker:
                break
        return {"items": items}


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def cmd_create_app(client: AppMarketClient, args):
    result = client.create_app(args.name, args.desc, args.type)
    app_id = result.get("appID", "")
    print(f"应用创建成功！AppID: {app_id}")
    print(f"\n下一步: appmarket-cli.py create-version --app-id {app_id} --deploy-meta deploy-meta.json")


def cmd_get_app(client: AppMarketClient, args):
    print(json.dumps(client.get_app(args.app_id), indent=2, ensure_ascii=False))


def cmd_update_app(client: AppMarketClient, args):
    if not args.name and not args.desc:
        print("错误: 请至少提供 --name 或 --desc 中的一个", file=sys.stderr)
        sys.exit(1)
    client.patch_app(args.app_id, name=args.name or "", description=args.desc or "")
    print(f"应用更新成功！App: {args.app_id}")
    if args.name:
        print(f"  名称: {args.name}")
    if args.desc:
        print(f"  描述: {args.desc[:60]}{'...' if len(args.desc) > 60 else ''}")


def cmd_list_apps(client: AppMarketClient, _args):
    print(json.dumps(client.list_apps(), indent=2, ensure_ascii=False))


def cmd_create_version(client: AppMarketClient, args):
    deploy_meta = _load_json_file(args.deploy_meta)
    description = args.desc or f"版本 {args.version}"
    client.create_version(args.app_id, args.version, description, deploy_meta)
    print(f"版本创建成功！App: {args.app_id}  Version: {args.version}  Status: Draft")
    print(f"\n下一步:")
    print(f"  测试:  appmarket-cli.py test-version --app-id {args.app_id} --version {args.version}")
    print(f"  发布:  appmarket-cli.py publish-version --app-id {args.app_id} --version {args.version}")


def cmd_update_version(client: AppMarketClient, args):
    deploy_meta = _load_json_file(args.deploy_meta)
    client.update_version(args.app_id, args.version, deploy_meta, args.desc)
    print(f"版本更新成功！App: {args.app_id}  Version: {args.version}")


def cmd_get_version(client: AppMarketClient, args):
    print(json.dumps(client.get_version(args.app_id, args.version), indent=2, ensure_ascii=False))


def cmd_list_versions(client: AppMarketClient, args):
    print(json.dumps(client.list_versions(args.app_id), indent=2, ensure_ascii=False))


def cmd_test_version(client: AppMarketClient, args):
    ver_info = client.get_version(args.app_id, args.version)
    status = ver_info.get("status", "")
    if status != "Draft":
        print(f"错误: 版本状态为 {status}，只能测试 Draft 版本", file=sys.stderr)
        sys.exit(1)

    print(f"测试 Draft 版本: {args.app_id} {args.version}")
    print("-" * 40)
    print("说明: test-version 会在目标区域内部调用 create-instance 创建 AppInstance 进行验收。")

    # 准备输入参数
    if args.inputs:
        inputs = _load_json_file(args.inputs)
    else:
        # 使用 inputPreset 时只需传 preset 未覆盖的 required 字段（如 sensitive 密码/密钥）
        deploy_meta = ver_info.get("deployMeta", {})
        schema = deploy_meta.get("inputSchema", {})
        presets = deploy_meta.get("inputPresets", [])
        preset_inputs = presets[0].get("inputs", {}) if presets else {}

        required = set(schema.get("required", []))
        inputs = {}
        for name, prop in schema.get("properties", {}).items():
            # 跳过 preset 已覆盖的字段
            if name in preset_inputs:
                continue
            # 只传 required 且无 default 的字段（通常是 sensitive 字段）
            if name in required and "default" not in prop:
                placeholder = "Test@1234" if "password" in name.lower() else f"test-{name}"
                inputs[name] = placeholder
                print(f"  需要手动提供: {name} (当前使用占位值 '{placeholder}')")
        print(f"使用 InputPreset '{presets[0]['name'] if presets else 'N/A'}' + 补充 inputs: {json.dumps(inputs, ensure_ascii=False)}")

    region = args.region
    print(f"区域: {region}")

    # 创建测试实例
    print("\n创建测试实例...")
    inst = client.create_instance(args.app_id, args.version, inputs, region)
    instance_id = inst.get("appInstanceID", "") or inst.get("instanceID", "")
    print(f"实例 ID: {instance_id}")

    # 轮询状态（最多 10 分钟）
    print("\n等待部署完成...")
    final_status = ""
    for i in range(60):
        time.sleep(10)
        info = client.get_instance(args.app_id, instance_id, region)
        st = info.get("status", "")
        print(f"  [{(i + 1) * 10}s] {st}")
        if st in ("Running", "Deployed"):
            print(f"\n实例部署成功！状态: {st}")
            outputs = info.get("outputs", {})
            if outputs:
                print("\n实例输出:")
                for k, v in outputs.items():
                    print(f"  {k} = {v}")
            else:
                print("\n实例详情:")
                print(json.dumps(info, indent=2, ensure_ascii=False))
            final_status = st
            break
        if st in ("Failed", "DeployFailed"):
            print("\n实例部署失败！", file=sys.stderr)
            print(json.dumps(info, indent=2, ensure_ascii=False), file=sys.stderr)
            final_status = st
            break
    else:
        print("\n超时: 实例在 600 秒内未完成部署", file=sys.stderr)

    # 清理
    if args.cleanup:
        print(f"\n清理: 删除实例 {instance_id}...")
        client.delete_instance(args.app_id, instance_id, region)
        print("实例已删除")
    else:
        print(f"\n测试实例保留中，手动删除:")
        print(f"  appmarket-cli.py delete-instance --app-id {args.app_id} --instance-id {instance_id}")

    if final_status in ("Failed", "DeployFailed"):
        sys.exit(1)


def cmd_publish_version(client: AppMarketClient, args):
    ver_info = client.get_version(args.app_id, args.version)
    status = ver_info.get("status", "")
    if status != "Draft":
        print(f"错误: 版本状态为 {status}，只能发布 Draft 版本", file=sys.stderr)
        sys.exit(1)

    presets = ver_info.get("deployMeta", {}).get("inputPresets", [])

    print("=" * 50)
    print("        版本发布确认")
    print("=" * 50)
    print(f"App ID:   {args.app_id}")
    print(f"版本号:   {args.version}")
    print(f"状态:     {status}")
    if presets:
        print(f"\n规格配置 (共 {len(presets)} 个):")
        for p in presets:
            print(f"  - {p.get('name', '')} ({p.get('title', '')})")
    print("=" * 50)

    if not args.yes:
        confirm = input("\n确认发布？发布后不可修改 [y/N]: ").strip().lower()
        if confirm != "y":
            print("已取消发布")
            return

    print("\n发布中...")
    client.publish_version(args.app_id, args.version)

    # 轮询发布状态（最多 2.5 分钟）
    for i in range(30):
        time.sleep(5)
        info = client.get_version(args.app_id, args.version)
        st = info.get("status", "")
        if st == "Published":
            print(f"\n版本发布成功！App: {args.app_id}  Version: {args.version}")
            return
        print(f"  [{(i + 1) * 5}s] {st}...")

    print("\n发布超时，请手动查询状态:", file=sys.stderr)
    print(f"  appmarket-cli.py get-version --app-id {args.app_id} --version {args.version}", file=sys.stderr)


def cmd_get_instance(client: AppMarketClient, args):
    print(json.dumps(client.get_instance(args.app_id, args.instance_id), indent=2, ensure_ascii=False))


def cmd_delete_instance(client: AppMarketClient, args):
    client.delete_instance(args.app_id, args.instance_id)
    print(f"实例已删除: {args.instance_id}")


def cmd_list_instances(client: AppMarketClient, args):
    data = client.list_instances(args.app_id or "", args.region or "")
    items = data.get("items", [])
    if not items:
        print("没有找到 AppInstance")
        return
    print(json.dumps({"items": items}, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _load_json_file(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {path}: {e}", file=sys.stderr)
        sys.exit(1)


def _get_env_or_exit(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print(f"错误: 请设置环境变量 {name}", file=sys.stderr)
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AppMarket CLI — 应用市场开发者命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("APPMARKET_API_BASE", "https://ecs.qiniuapi.com"),
        help="API 基地址 (默认: https://ecs.qiniuapi.com)",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # create-app
    p = sub.add_parser("create-app", help="创建新应用")
    p.add_argument("--name", required=True, help="应用名称 (2-60 字符)")
    p.add_argument("--desc", required=True, help="应用描述 (50-10000 字符)")
    p.add_argument("--type", default="Private", choices=["Private", "Managed"],
                   help="应用类型 (默认: Private)")

    # get-app
    p = sub.add_parser("get-app", help="获取应用详情")
    p.add_argument("--app-id", required=True, help="应用 ID")

    # update-app
    p = sub.add_parser("update-app", help="更新应用信息（名称/描述）")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--name", default="", help="新的应用名称 (2-60 字符)")
    p.add_argument("--desc", default="", help="新的应用描述 (50-10000 字符)")

    # list-apps
    sub.add_parser("list-apps", help="列出所有应用")

    # create-version
    p = sub.add_parser("create-version", help="创建应用版本")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--version", default="1.0.0", help="版本号 (默认: 1.0.0)")
    p.add_argument("--desc", help="版本描述")
    p.add_argument("--deploy-meta", required=True, help="DeployMeta JSON 文件路径")

    # update-version
    p = sub.add_parser("update-version", help="更新 Draft 版本")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--version", required=True, help="版本号")
    p.add_argument("--desc", required=True, help="版本描述（必填，API 要求）")
    p.add_argument("--deploy-meta", required=True, help="DeployMeta JSON 文件路径")

    # get-version
    p = sub.add_parser("get-version", help="获取版本详情")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--version", required=True, help="版本号")

    # list-versions
    p = sub.add_parser("list-versions", help="列出应用的所有版本")
    p.add_argument("--app-id", required=True, help="应用 ID")

    # test-version
    p = sub.add_parser("test-version", help="测试 Draft 版本（创建实例并监控部署）")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--version", required=True, help="版本号")
    p.add_argument("--inputs", help="输入参数 JSON 文件路径")
    p.add_argument("--region", default="ap-northeast-1", help="部署区域 (默认: ap-northeast-1)")
    p.add_argument("--cleanup", action="store_true", help="测试后自动删除实例")

    # publish-version
    p = sub.add_parser("publish-version", help="发布版本（发布后不可修改）")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--version", required=True, help="版本号")
    p.add_argument("--yes", "-y", action="store_true", help="跳过确认直接发布")

    # get-instance
    p = sub.add_parser("get-instance", help="获取实例详情")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--instance-id", required=True, help="实例 ID")

    # delete-instance
    p = sub.add_parser("delete-instance", help="删除实例")
    p.add_argument("--app-id", required=True, help="应用 ID")
    p.add_argument("--instance-id", required=True, help="实例 ID")

    # list-instances
    p = sub.add_parser("list-instances", help="列出实例")
    p.add_argument("--app-id", help="应用 ID（可选）")
    p.add_argument("--region", default="ap-northeast-1", help="区域（默认: ap-northeast-1）")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    ak = _get_env_or_exit("QINIU_ACCESS_KEY")
    sk = _get_env_or_exit("QINIU_SECRET_KEY")
    client = AppMarketClient(ak, sk, args.api_base)

    commands = {
        "create-app": cmd_create_app,
        "get-app": cmd_get_app,
        "update-app": cmd_update_app,
        "list-apps": cmd_list_apps,
        "create-version": cmd_create_version,
        "update-version": cmd_update_version,
        "get-version": cmd_get_version,
        "list-versions": cmd_list_versions,
        "test-version": cmd_test_version,
        "publish-version": cmd_publish_version,
        "get-instance": cmd_get_instance,
        "delete-instance": cmd_delete_instance,
        "list-instances": cmd_list_instances,
    }

    handler = commands.get(args.command)
    if handler:
        handler(client, args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
