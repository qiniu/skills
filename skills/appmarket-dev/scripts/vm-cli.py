#!/usr/bin/env python3
"""vm-cli — LAS VM 实例管理工具（零第三方依赖）。

用于创建、查询和删除 LAS VM 实例，以及查询可用机型。
镜像制作相关操作请使用 image-cli.py。

用法:
    vm-cli.py create-vm   [--region REGION] [options]
    vm-cli.py delete-vm   --instance-id ID [--region REGION]
    vm-cli.py list-vms    [--region REGION]
    vm-cli.py list-types  [--region REGION] [--family FAMILY]

示例:
    # 创建临时 VM（用于调试安装脚本）
    vm-cli.py create-vm --region cn-hongkong-1

    # 列出当前区域所有 VM（排查残留）
    vm-cli.py list-vms --region ap-northeast-1

    # 删除残留 VM
    vm-cli.py delete-vm --instance-id i-xxxxx

    # 查看可用机型
    vm-cli.py list-types --region ap-northeast-1 --family t1

环境变量:
    QINIU_ACCESS_KEY   七牛 AccessKey（必需）
    QINIU_SECRET_KEY   七牛 SecretKey（必需）
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import shutil
import ssl
import string
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Qiniu 签名 & HTTP
# ---------------------------------------------------------------------------

def qiniu_sign(access_key: str, secret_key: str, method: str, url: str,
               content_type: str = "", body: str = "") -> str:
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


class _Response:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.body = body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> dict:
        return json.loads(self.body)


def _http_request(method: str, url: str, headers: dict, body_bytes: bytes | None = None) -> _Response:
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return _Response(resp.status, resp.read())
    except urllib.error.HTTPError as e:
        return _Response(e.code, e.read())


# ---------------------------------------------------------------------------
# LAS API 客户端（VM 相关）
# ---------------------------------------------------------------------------

class LASClient:
    def __init__(self, access_key: str, secret_key: str):
        self.ak = access_key
        self.sk = secret_key

    def _base(self, region_id: str) -> str:
        return f"https://{region_id}-ecs.qiniuapi.com"

    def _request(self, method: str, region_id: str, path: str, json_body=None) -> _Response:
        url = f"{self._base(region_id)}{path}"
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

    def _check(self, resp: _Response, expected: tuple[int, ...] = (200,)):
        if resp.status_code not in expected:
            print(f"API 请求失败 [{resp.status_code}]", file=sys.stderr)
            try:
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False), file=sys.stderr)
            except Exception:
                print(resp.text, file=sys.stderr)
            sys.exit(1)
        if resp.status_code == 204 or not resp.body:
            return {}
        return resp.json()

    def list_official_images(self, region_id: str, state: str = "Available"):
        """查询官方镜像（带分页）。用于自动选择 Ubuntu 基础镜像。"""
        items = []
        marker = ""
        while True:
            query = f"type=Official&state={state}"
            if marker:
                query += f"&marker={marker}"
            resp = self._check(self._request("GET", region_id, f"/v1/images?{query}"))
            batch = resp if isinstance(resp, list) else resp.get("items", resp.get("data", []))
            items.extend(batch)
            marker = resp.get("nextMarker", "") if isinstance(resp, dict) else ""
            if not marker:
                break
        return {"items": items}

    def list_instance_types(self, region_id: str, family: str = ""):
        query = "/v1/instance-types?limit=100"
        if family:
            query += f"&family={family}"
        return self._check(self._request("GET", region_id, query))

    def create_instance(self, region_id: str, instance_type: str, image_id: str,
                        disk_type: str, disk_size: int, bandwidth: int,
                        password: str, name: str, description: str = ""):
        body: dict = {
            "regionID": region_id,
            "instanceType": instance_type,
            "imageID": image_id,
            "systemDisk": {"diskType": disk_type, "size": disk_size},
            "internetMaxBandwidth": bandwidth,
            "internetCost": {"chargeType": "PeakBandwidth"},
            "password": password,
            "clientToken": str(uuid.uuid4()),
            "names": [name],
        }
        if description:
            body["description"] = description[:100]  # API 限制 100 字符
        return self._check(self._request("POST", region_id, "/v1/instances", json_body=body))

    def get_instance(self, region_id: str, instance_id: str):
        return self._check(self._request("GET", region_id, f"/v1/instances/{instance_id}"))

    def list_instances(self, region_id: str):
        """列出实例（带分页）。"""
        items = []
        marker = ""
        while True:
            query = "/v1/instances"
            if marker:
                query += f"?marker={marker}"
            resp = self._check(self._request("GET", region_id, query))
            batch = resp if isinstance(resp, list) else resp.get("items", resp.get("data", []))
            items.extend(batch)
            marker = resp.get("nextMarker", "") if isinstance(resp, dict) else ""
            if not marker:
                break
        return {"items": items}

    def delete_instance(self, region_id: str, instance_id: str):
        return self._check(
            self._request("DELETE", region_id, f"/v1/instances/{instance_id}"),
            expected=(200, 202, 204),
        )


# ---------------------------------------------------------------------------
# SSH 辅助函数
# ---------------------------------------------------------------------------

def _generate_password() -> str:
    """生成符合 LAS 密码策略的随机密码（大写+小写+数字+特殊字符）。"""
    upper = random.choices(string.ascii_uppercase, k=4)
    lower = random.choices(string.ascii_lowercase, k=4)
    digits = random.choices(string.digits, k=4)
    special = random.choices("@#$%&*", k=2)
    pool = upper + lower + digits + special
    random.shuffle(pool)
    return "".join(pool)


def _ssh_cmd_base(ip: str, password: str, user: str) -> list[str]:
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
    if password:
        if not shutil.which("sshpass"):
            print("错误: 需要安装 sshpass (apt install sshpass / brew install sshpass)", file=sys.stderr)
            sys.exit(1)
        return ["sshpass", "-p", password, "ssh"] + ssh_opts + [f"{user}@{ip}"]
    return ["ssh"] + ssh_opts + [f"{user}@{ip}"]


def _wait_vm_running(client: LASClient, region: str, instance_id: str,
                     timeout: int = 300) -> str:
    """轮询 VM 状态直到 Running，返回公网 IP。"""
    print("等待 VM 启动...")
    for i in range(timeout // 10):
        time.sleep(10)
        info = client.get_instance(region, instance_id)
        state = info.get("state", "")
        print(f"  [{(i + 1) * 10}s] {state}")
        if state == "Running":
            pub_ips = info.get("publicIPAddresses", [])
            if not pub_ips:
                print("错误: VM 没有公网 IP", file=sys.stderr)
                sys.exit(1)
            ip = pub_ips[0].get("ipv4", "")
            print(f"VM 就绪！公网 IP: {ip}")
            return ip
        if state in ("Failed", "Error"):
            print(f"错误: VM 启动失败 ({state})", file=sys.stderr)
            sys.exit(1)
    print("错误: VM 启动超时", file=sys.stderr)
    sys.exit(1)


def _wait_ssh(ip: str, password: str, user: str, timeout: int = 120):
    """等待 SSH 连接就绪。"""
    print("等待 SSH 就绪...")
    for i in range(timeout // 5):
        time.sleep(5)
        try:
            full_cmd = _ssh_cmd_base(ip, password, user) + ["echo ok"]
            result = subprocess.run(full_cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                print("SSH 连接成功")
                return
        except subprocess.TimeoutExpired:
            pass
        if (i + 1) % 4 == 0:
            print(f"  [{(i + 1) * 5}s] 重试中...")
    print("错误: SSH 连接超时", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------

def _make_client() -> LASClient:
    ak = os.environ.get("QINIU_ACCESS_KEY", "")
    sk = os.environ.get("QINIU_SECRET_KEY", "")
    if not ak or not sk:
        print("错误: 请设置环境变量 QINIU_ACCESS_KEY 和 QINIU_SECRET_KEY", file=sys.stderr)
        sys.exit(1)
    return LASClient(ak, sk)


def _pick_smallest_type(client: LASClient, region: str) -> str:
    data = client.list_instance_types(region)
    items = data if isinstance(data, list) else data.get("items", data.get("data", []))
    available = [t for t in items
                 if region in t.get("regions", []) and not t.get("gpuCount")]
    if not available:
        print("错误: 未找到可用机型，请用 --instance-type 手动指定", file=sys.stderr)
        sys.exit(1)
    available.sort(key=lambda t: (t.get("cpu", 0), t.get("memory", 0)))
    return available[0]["instanceType"]


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def cmd_list_vms(args):
    client = _make_client()
    region = args.region
    data = client.list_instances(region)
    items = data if isinstance(data, list) else data.get("items", data.get("data", []))
    if not items:
        print(f"区域 {region} 没有 VM 实例")
        return
    print(f"区域 {region} 共 {len(items)} 个 VM 实例:\n")
    print(f"  {'实例 ID':<30s}  {'状态':<12s}  {'公网 IP':<16s}  {'名称'}")
    print(f"  {'-' * 30}  {'-' * 12}  {'-' * 16}  {'-' * 20}")
    for inst in items:
        pub_ips = inst.get("publicIPAddresses", [])
        ip = pub_ips[0].get("ipv4", "") if pub_ips else "-"
        print(f"  {inst.get('id', ''):<30s}  {inst.get('state', ''):<12s}  {ip:<16s}  {inst.get('name', '')}")


def cmd_list_types(args):
    client = _make_client()
    region = args.region
    data = client.list_instance_types(region, args.family)
    items = data if isinstance(data, list) else data.get("items", data.get("data", []))
    available = [t for t in items
                 if region in t.get("regions", []) and not t.get("gpuCount")]
    available.sort(key=lambda t: (t.get("cpu", 0), t.get("memory", 0)))
    if not available:
        print(f"区域 {region} 没有可用机型")
        return
    print(f"区域 {region} 可用机型 (共 {len(available)} 个，不含 GPU):\n")
    print(f"  {'机型':<24s}  {'CPU':>4s}  {'内存(GiB)':>9s}  {'规格族':<10s}  {'分类'}")
    print(f"  {'-' * 24}  {'-' * 4}  {'-' * 9}  {'-' * 10}  {'-' * 10}")
    for t in available:
        print(f"  {t.get('instanceType', ''):<24s}  {t.get('cpu', 0):>4d}  {t.get('memory', 0):>9.1f}  {t.get('family', ''):<10s}  {t.get('category', '')}")


def cmd_delete_vm(args):
    client = _make_client()
    print(f"删除 VM: {args.instance_id} (region: {args.region})...")
    client.delete_instance(args.region, args.instance_id)
    print("VM 已删除")


def cmd_create_vm(args):
    """创建临时 VM 并等待 SSH 就绪（供手动调试安装脚本）。"""
    client = _make_client()
    region = args.region
    password = args.password or _generate_password()

    instance_type = args.instance_type
    if not instance_type:
        print("查询最小可用机型...")
        instance_type = _pick_smallest_type(client, region)
        print(f"自动选择机型: {instance_type}")

    if args.base_image:
        base_image = args.base_image
        print(f"使用指定基础镜像: {base_image}")
    else:
        print("查询 Ubuntu 24.04 官方镜像...")
        images = client.list_official_images(region)
        items = images if isinstance(images, list) else images.get("items", images.get("data", []))
        ubuntu = [i for i in items
                  if i.get("osDistribution") == "Ubuntu" and "24.04" in i.get("osVersion", "")]
        if not ubuntu:
            print("错误: 未找到 Ubuntu 24.04 官方镜像", file=sys.stderr)
            sys.exit(1)
        base_image = ubuntu[0]["id"]
        print(f"基础镜像: {base_image} ({ubuntu[0].get('name', '')})")

    vm_name = args.name or "image-builder"
    print(f"\n创建 VM: {vm_name} ({instance_type}, {args.disk_size}GB {args.disk_type})...")
    result = client.create_instance(region, instance_type, base_image,
                                    args.disk_type, args.disk_size, args.bandwidth,
                                    password, vm_name)
    instance_id = result["instanceIDs"][0]
    print(f"VM 创建成功: {instance_id}")

    public_ip = _wait_vm_running(client, region, instance_id)
    _wait_ssh(public_ip, password, args.ssh_user)

    print(f"\n{'=' * 56}")
    print(f"  VM 就绪！")
    print(f"  Instance ID: {instance_id}")
    print(f"  IP:          {public_ip}")
    print(f"  Password:    {password}")
    print(f"  SSH:         sshpass -p '{password}' ssh {args.ssh_user}@{public_ip}")
    print(f"")
    print(f"  调试完成后用 image-cli.py 创建镜像:")
    print(f"    python3 image-cli.py create-image \\")
    print(f"      --instance-id {instance_id} \\")
    print(f"      --image-name <镜像名称> \\")
    print(f"      --password '{password}'")
    print(f"")
    print(f"  或直接删除 VM:")
    print(f"    python3 vm-cli.py delete-vm --instance-id {instance_id} --region {region}")
    print(f"{'=' * 56}")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="vm-cli — LAS VM 实例管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  # 创建临时 VM 供手动调试安装脚本
  %(prog)s create-vm --region cn-hongkong-1

  # 列出区域内所有 VM（排查残留）
  %(prog)s list-vms --region ap-northeast-1

  # 删除残留 VM
  %(prog)s delete-vm --instance-id i-xxxxx --region ap-northeast-1

  # 查看可用机型
  %(prog)s list-types --region ap-northeast-1 --family t1

环境变量:
  QINIU_ACCESS_KEY   七牛 AccessKey（必需）
  QINIU_SECRET_KEY   七牛 SecretKey（必需）""",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # create-vm
    p = sub.add_parser("create-vm", help="创建临时 VM（供手动调试安装脚本）",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", default="", help="VM 名称 (默认: image-builder)")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")
    p.add_argument("--instance-type", help="VM 规格 (默认: 自动选择最小可用机型)")
    p.add_argument("--disk-type", default="cloud.ssd", choices=["local.ssd", "cloud.ssd"],
                   help="磁盘类型 (默认: cloud.ssd)")
    p.add_argument("--disk-size", type=int, default=40, help="系统盘大小 GB (默认: 40)")
    p.add_argument("--bandwidth", type=int, default=100, choices=[50, 100, 200],
                   help="峰值带宽 Mbps，可选 50/100/200 (默认: 100)")
    p.add_argument("--base-image", help="基础镜像 ID (默认: 自动查询 Ubuntu 24.04)")
    p.add_argument("--password", help="VM 密码 (默认: 随机生成)")
    p.add_argument("--ssh-user", default="root", help="SSH 用户名 (默认: root)")

    # delete-vm
    p = sub.add_parser("delete-vm", help="删除 VM 实例")
    p.add_argument("--instance-id", required=True, help="实例 ID")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")

    # list-vms
    p = sub.add_parser("list-vms", help="列出 VM 实例（排查残留）")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")

    # list-types
    p = sub.add_parser("list-types", help="列出可用机型")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")
    p.add_argument("--family", default="", help="按规格族过滤 (如 t1, t2)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "create-vm":  cmd_create_vm,
        "delete-vm":  cmd_delete_vm,
        "list-vms":   cmd_list_vms,
        "list-types": cmd_list_types,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
