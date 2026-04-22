#!/usr/bin/env python3
"""image-cli — LAS 镜像管理与制作工具（零第三方依赖）。

全自动制作流程: 创建 VM → SSH 执行安装脚本 → 清理环境 → 创建镜像 → 删除 VM
VM 的查询/删除等底层操作请使用 vm-cli.py。

用法:
    image-cli.py build         --install-script FILE --image-name NAME [options]
    image-cli.py create-image  --instance-id ID --image-name NAME [options]
    image-cli.py update-image  --image-id ID [--name NAME] [--desc DESC] [--state STATE] ...
    image-cli.py list-images   [--region REGION] [--type TYPE] [--name NAME]
    image-cli.py delete-image  --image-id ID [--region REGION]

镜像名称约束: 只含大小写字母、数字、短划线、点，长度 2-60。
镜像描述约束: 最大 100 UTF8 字符（超出时自动截断）。

示例:
    # 一键制作自定义镜像（自动选最小机型，完成后删除 VM）
    image-cli.py build --install-script path/to/install.sh \\
                       --image-name MyApp-v1.0.0

    # 分步制作：先用 vm-cli.py create-vm 调试，再创建镜像
    image-cli.py create-image --instance-id i-xxxxx \\
                              --image-name MyApp-v1.0.0 \\
                              --password 'VM密码'

    # 列出所有自定义镜像
    image-cli.py list-images --region cn-hongkong-1

    # 更新镜像描述
    image-cli.py update-image --image-id image-xxxxx --desc "Ubuntu 24.04 + MyApp v1.0"

    # 废弃旧镜像
    image-cli.py update-image --image-id image-xxxxx --state Deprecated

    # 删除镜像
    image-cli.py delete-image --image-id image-xxxxx

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
import secrets
import shutil
import ssl
import string
import uuid
import subprocess
import sys
import time
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
    try:
        with urllib.request.urlopen(req, context=_SSL_CONTEXT) as resp:
            return _Response(resp.status, resp.read())
    except urllib.error.HTTPError as e:
        return _Response(e.code, e.read())


_SSL_CONTEXT = ssl.create_default_context()


# ---------------------------------------------------------------------------
# LAS API 客户端（VM + Image）
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

    # ---- Image ----

    def list_images(self, region_id: str, image_type: str = "Custom", state: str = ""):
        """列出镜像（支持分页）。state 为空时返回所有状态（Custom 镜像常用）。"""
        items = []
        marker = ""
        while True:
            query = f"type={image_type}"
            if state:
                query += f"&state={state}"
            if marker:
                query += f"&marker={marker}"
            resp = self._check(self._request("GET", region_id, f"/v1/images?{query}"))
            batch = resp if isinstance(resp, list) else resp.get("items", resp.get("data", []))
            items.extend(batch)
            marker = resp.get("nextMarker", "") if isinstance(resp, dict) else ""
            if not marker:
                break
        return {"items": items}

    def get_image(self, region_id: str, image_id: str):
        return self._check(self._request("GET", region_id, f"/v1/images/{image_id}"))

    def create_image(self, region_id: str, instance_id: str, name: str, description: str = ""):
        # description 最大 100 UTF8 字符（API 约束）
        if description and len(description.encode("utf-8")) > 100:
            description = description.encode("utf-8")[:100].decode("utf-8", errors="ignore")
        body: dict = {"instanceID": instance_id, "regionID": region_id, "name": name}
        if description:
            body["description"] = description
        return self._check(
            self._request("POST", region_id, "/v1/images", json_body=body),
            expected=(200, 201, 202),
        )

    def patch_image(self, region_id: str, image_id: str, **kwargs):
        """更新镜像元信息（PATCH /v1/images/{imageID}）。
        支持字段: name, description, state (Available/Deprecated/Disabled),
                  public (bool), min_cpu (int), min_memory (float), min_disk (int)。
        """
        body = {}
        if "name" in kwargs and kwargs["name"]:
            body["name"] = kwargs["name"]
        if "description" in kwargs and kwargs["description"] is not None:
            desc = kwargs["description"]
            if len(desc.encode("utf-8")) > 100:
                desc = desc.encode("utf-8")[:100].decode("utf-8", errors="ignore")
            body["description"] = desc
        if "state" in kwargs and kwargs["state"]:
            body["state"] = kwargs["state"]
        if "public" in kwargs and kwargs["public"] is not None:
            body["public"] = kwargs["public"]
        if "min_cpu" in kwargs and kwargs["min_cpu"] is not None:
            body["minCPU"] = kwargs["min_cpu"]
        if "min_memory" in kwargs and kwargs["min_memory"] is not None:
            body["minMemory"] = kwargs["min_memory"]
        if "min_disk" in kwargs and kwargs["min_disk"] is not None:
            body["minDisk"] = kwargs["min_disk"]
        return self._check(
            self._request("PATCH", region_id, f"/v1/images/{image_id}", json_body=body),
            expected=(200, 204),
        )

    def delete_image(self, region_id: str, image_id: str):
        return self._check(
            self._request("DELETE", region_id, f"/v1/images/{image_id}"),
            expected=(200, 202, 204),
        )

    # ---- Instance ----

    def list_instance_types(self, region_id: str, family: str = ""):
        items = []
        marker = ""
        while True:
            query = "/v1/instance-types?limit=100"
            if family:
                query += f"&family={family}"
            if marker:
                query += f"&marker={marker}"
            resp = self._check(self._request("GET", region_id, query))
            batch = resp if isinstance(resp, list) else resp.get("items", resp.get("data", []))
            items.extend(batch)
            marker = resp.get("nextMarker", "") if isinstance(resp, dict) else ""
            if not marker:
                break
        return {"items": items}

    def create_instance(self, region_id: str, instance_type: str, image_id: str,
                        disk_type: str, disk_size: int, bandwidth: int,
                        password: str, name: str):
        return self._check(self._request("POST", region_id, "/v1/instances", json_body={
            "regionID": region_id,
            "instanceType": instance_type,
            "imageID": image_id,
            "systemDisk": {"diskType": disk_type, "size": disk_size},
            "internetMaxBandwidth": bandwidth,
            "internetCost": {"chargeType": "PeakBandwidth"},
            "password": password,
            "clientToken": str(uuid.uuid4()),
            "names": [name],
        }))

    def get_instance(self, region_id: str, instance_id: str):
        return self._check(self._request("GET", region_id, f"/v1/instances/{instance_id}"))

    def delete_instance(self, region_id: str, instance_id: str):
        return self._check(
            self._request("DELETE", region_id, f"/v1/instances/{instance_id}"),
            expected=(200, 202, 204),
        )


# ---------------------------------------------------------------------------
# SSH / 清理辅助函数
# ---------------------------------------------------------------------------

SSH_CONNECT_TIMEOUT = 10
SSH_EXEC_TIMEOUT = int(os.environ.get("APPMARKET_SSH_EXEC_TIMEOUT", "1800"))
SSH_CLEANUP_TIMEOUT = int(os.environ.get("APPMARKET_SSH_CLEANUP_TIMEOUT", "900"))


def _generate_password() -> str:
    """生成符合 LAS 密码策略的随机密码。"""
    rng = secrets.SystemRandom()
    pool = [
        rng.choice(string.ascii_uppercase) for _ in range(4)
    ] + [
        rng.choice(string.ascii_lowercase) for _ in range(4)
    ] + [
        rng.choice(string.digits) for _ in range(4)
    ] + [
        rng.choice("@#$%&*") for _ in range(2)
    ]
    rng.shuffle(pool)
    return "".join(pool)


def _sshpass_env(password: str) -> dict[str, str] | None:
    if not password:
        return None
    env = os.environ.copy()
    env["SSHPASS"] = password
    return env


def _ssh_cmd_base(ip: str, password: str, user: str) -> list[str]:
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}"]
    if password:
        if not shutil.which("sshpass"):
            print("错误: 需要安装 sshpass (apt install sshpass / brew install sshpass)", file=sys.stderr)
            sys.exit(1)
        return ["sshpass", "-e", "ssh"] + ssh_opts + [f"{user}@{ip}"]
    return ["ssh"] + ssh_opts + [f"{user}@{ip}"]


def _scp_cmd_base(password: str) -> list[str]:
    scp_opts = ["-o", "StrictHostKeyChecking=no", f"-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}"]
    if password:
        return ["sshpass", "-e", "scp"] + scp_opts
    return ["scp"] + scp_opts


def _ssh_exec(ip: str, password: str, user: str, cmd: str, timeout: int = SSH_EXEC_TIMEOUT) -> int:
    """在远端 VM 上执行命令。stdin 始终重定向到 /dev/null，确保不会因交互式提示挂住。"""
    full_cmd = _ssh_cmd_base(ip, password, user) + [cmd]
    result = subprocess.run(full_cmd, stdin=subprocess.DEVNULL, timeout=timeout, env=_sshpass_env(password))
    return result.returncode


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
    print("等待 SSH 就绪...")
    for i in range(timeout // 5):
        time.sleep(5)
        try:
            full_cmd = _ssh_cmd_base(ip, password, user) + ["echo ok"]
            result = subprocess.run(full_cmd, capture_output=True, timeout=10, env=_sshpass_env(password))
            if result.returncode == 0:
                print("SSH 连接成功")
                return
        except subprocess.TimeoutExpired:
            pass
        if (i + 1) % 4 == 0:
            print(f"  [{(i + 1) * 5}s] 重试中...")
    print("错误: SSH 连接超时", file=sys.stderr)
    sys.exit(1)


def _wait_image_available(client: LASClient, region: str, image_id: str,
                          timeout: int = 600):
    print("等待镜像就绪...")
    for i in range(timeout // 10):
        time.sleep(10)
        info = client.get_image(region, image_id)
        state = info.get("state", "")
        print(f"  [{(i + 1) * 10}s] {state}")
        if state == "Available":
            return info
        if state in ("Failed", "Error"):
            print(f"错误: 镜像创建失败 ({state})", file=sys.stderr)
            sys.exit(1)
    print("错误: 镜像创建超时", file=sys.stderr)
    sys.exit(1)


def _ssh_run_script(ip: str, password: str, user: str, script_path: str):
    """上传安装脚本到 VM 并执行。"""
    if not os.path.isfile(script_path):
        print(f"错误: 安装脚本不存在: {script_path}", file=sys.stderr)
        sys.exit(1)

    remote_path = "/root/_install.sh"
    print(f"\n上传安装脚本: {script_path} -> {remote_path}")
    scp_cmd = _scp_cmd_base(password) + [script_path, f"{user}@{ip}:{remote_path}"]
    rc = subprocess.run(scp_cmd, env=_sshpass_env(password), timeout=SSH_EXEC_TIMEOUT).returncode
    if rc != 0:
        print("错误: 上传安装脚本失败", file=sys.stderr)
        sys.exit(1)

    print("执行安装脚本...")
    rc = _ssh_exec(ip, password, user, f"chmod +x {remote_path} && bash {remote_path}")
    if rc != 0:
        print(f"错误: 安装脚本执行失败 (exit code {rc})", file=sys.stderr)
        sys.exit(1)

    _ssh_exec(ip, password, user, f"rm -f {remote_path}")
    print("安装脚本执行完成")


def _ssh_cleanup(ip: str, password: str, user: str):
    """在 VM 上执行标准清理操作（为镜像制作准备）。"""
    print("\n清理环境...")
    cleanup_cmds = " && ".join([
        "apt-get clean",
        "apt-get autoremove -y",
        "rm -rf /var/lib/apt/lists/*",
        "journalctl --vacuum-time=1d",
        "rm -rf /tmp/* /var/tmp/*",
        "rm -f /etc/ssh/ssh_host_*",
        "cloud-init clean --logs",
        "rm -f /root/.bash_history /home/*/.bash_history",
    ])
    rc = _ssh_exec(ip, password, user, cleanup_cmds, timeout=SSH_CLEANUP_TIMEOUT)
    if rc != 0:
        print("警告: 部分清理命令失败，继续制作镜像", file=sys.stderr)
    print("清理完成")


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------

def _write_build_manifest(
    *,
    region: str,
    base_image: dict,
    builder_vm: dict,
    install_script_path: str | None,
    output_image: dict,
    manifest_dir: str = ".",
) -> str:
    """写出镜像构建 manifest（JSON），返回写入的文件路径。

    manifest 记录构建上下文，应提交进版本控制，以便：
    - 人工审阅镜像内容的确定性
    - 在需要时复现相同镜像
    """
    import datetime

    script_info: dict = {}
    if install_script_path and os.path.isfile(install_script_path):
        with open(install_script_path, "rb") as f:
            content_bytes = f.read()
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        script_info = {
            "path": os.path.abspath(install_script_path),
            "sha256": sha256,
        }

    manifest = {
        "builtAt": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "region": region,
        "baseImage": base_image,
        "builderVM": builder_vm,
        "installScript": script_info,
        "outputImage": output_image,
    }

    ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    image_name = output_image.get("name", "image")
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in image_name)
    filename = f"{safe_name}-build-{ts}.json"
    filepath = os.path.join(manifest_dir, filename)

    os.makedirs(manifest_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return filepath


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


def _check_ssh_deps() -> None:
    """前置检查 SSH 相关依赖，在任何 VM 操作前调用，fail-fast 避免资源浪费。"""
    missing = []
    if not shutil.which("ssh"):
        missing.append("ssh")
    if not shutil.which("scp"):
        missing.append("scp")
    if not shutil.which("sshpass"):
        missing.append("sshpass  # apt install sshpass  /  brew install sshpass")
    if missing:
        print("错误: 以下命令未找到，请先安装后重试：", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def cmd_list_images(args):
    client = _make_client()
    region = args.region
    data = client.list_images(region, image_type=args.type)
    items = data if isinstance(data, list) else data.get("items", data.get("data", []))
    if args.name:
        items = [i for i in items if args.name.lower() in i.get("name", "").lower()]
    if not items:
        print(f"区域 {region} 没有匹配的 {args.type} 类型镜像")
        return
    print(f"区域 {region} 共 {len(items)} 个 {args.type} 类型镜像:\n")
    print(f"  {'镜像 ID':<30s}  {'状态':<12s}  {'名称'}")
    print(f"  {'-' * 30}  {'-' * 12}  {'-' * 30}")
    for img in items:
        print(f"  {img.get('id', ''):<30s}  {img.get('state', ''):<12s}  {img.get('name', '')}")


def cmd_delete_image(args):
    client = _make_client()
    print(f"删除镜像: {args.image_id} (region: {args.region})...")
    client.delete_image(args.region, args.image_id)
    print("镜像已删除")


def cmd_update_image(args):
    """更新镜像元信息（name/description/state/public/minCPU/minMemory/minDisk）。"""
    client = _make_client()
    kwargs = {}
    if args.name:
        kwargs["name"] = args.name
    if args.desc is not None:
        kwargs["description"] = args.desc
    if args.state:
        kwargs["state"] = args.state
    if args.public is not None:
        kwargs["public"] = args.public
    if args.min_cpu is not None:
        kwargs["min_cpu"] = args.min_cpu
    if args.min_memory is not None:
        kwargs["min_memory"] = args.min_memory
    if args.min_disk is not None:
        kwargs["min_disk"] = args.min_disk

    if not kwargs:
        print("错误: 请至少提供一个要更新的字段", file=sys.stderr)
        sys.exit(1)

    client.patch_image(args.region, args.image_id, **kwargs)
    print(f"镜像已更新: {args.image_id}")
    for k, v in kwargs.items():
        print(f"  {k}: {v}")


def cmd_run_script(args):
    """在已有 VM 上重新执行安装脚本（用于 build 失败后迭代修复，无需重建 VM）。"""
    _check_ssh_deps()
    client = _make_client()
    region = args.region

    print(f"查询 VM: {args.instance_id}...")
    info = client.get_instance(region, args.instance_id)
    state = info.get("state", "")
    pub_ips = info.get("publicIPAddresses", [])
    public_ip = pub_ips[0].get("ipv4", "") if pub_ips else ""

    if state != "Running":
        print(f"错误: VM 状态为 {state}，需要 Running", file=sys.stderr)
        sys.exit(1)
    if not public_ip:
        print("错误: VM 没有公网 IP", file=sys.stderr)
        sys.exit(1)

    print(f"VM 就绪: {args.instance_id}, IP: {public_ip}")
    _wait_ssh(public_ip, args.password, args.ssh_user)
    _ssh_run_script(public_ip, args.password, args.ssh_user, args.install_script)
    print(f"\n脚本执行完成！")
    print(f"  VM:  {args.instance_id} ({public_ip})")
    print(f"  下一步（创建镜像）: python3 image-cli.py create-image \\")
    print(f"    --instance-id {args.instance_id} --region {region} \\")
    print(f"    --image-name <名称> --password '{args.password}'")


def cmd_get_image(args):
    """查询单个镜像详情。"""
    client = _make_client()
    info = client.get_image(args.region, args.image_id)
    print(json.dumps(info, indent=2, ensure_ascii=False))


def cmd_create_image(args):
    """从已有 VM 创建镜像（配合 vm-cli.py create-vm 分步制作）。"""
    _check_ssh_deps()
    client = _make_client()
    region = args.region
    instance_id = args.instance_id

    print(f"查询 VM: {instance_id}...")
    info = client.get_instance(region, instance_id)
    state = info.get("state", "")
    if state != "Running":
        print(f"错误: VM 状态为 {state}，需要 Running", file=sys.stderr)
        sys.exit(1)

    pub_ips = info.get("publicIPAddresses", [])
    public_ip = pub_ips[0].get("ipv4", "") if pub_ips else ""
    print(f"VM 状态: {state}, IP: {public_ip}")

    if not args.skip_cleanup:
        if not public_ip:
            print("错误: VM 没有公网 IP，无法 SSH 清理。使用 --skip-cleanup 跳过", file=sys.stderr)
            sys.exit(1)
        if not args.password:
            print("错误: 需要 --password 参数以 SSH 连接 VM 进行清理", file=sys.stderr)
            sys.exit(1)
        _ssh_cleanup(public_ip, args.password, args.ssh_user)

    desc = args.image_desc or ""
    print(f"\n创建镜像: {args.image_name}...")
    img = client.create_image(region, instance_id, args.image_name, desc)
    image_id = img.get("imageID", "")
    print(f"镜像创建中: {image_id}")

    _wait_image_available(client, region, image_id)

    # 查询镜像最终元数据
    img_info = client.get_image(region, image_id)
    min_disk = img_info.get("minDisk", args.disk_size)
    min_cpu  = img_info.get("minCPU", "?")
    min_mem  = img_info.get("minMemory", "?")

    print(f"\n{'=' * 50}")
    print(f"  镜像制作完成！")
    print(f"{'=' * 50}")
    print(json.dumps(img_info, indent=2, ensure_ascii=False))
    print(f"\n⚠  请在 variables.tf 中同步以下约束，否则创建实例时可能报 400：")
    print(f"   system_disk_size  minimum = {min_disk}")
    print(f"   instance_type     （需满足 CPU ≥ {min_cpu} 核、内存 ≥ {min_mem} GB）")

    # 写出构建 manifest（install_script 未知，仅记录 VM 和镜像信息）
    manifest_dir = os.getcwd()
    manifest_path = _write_build_manifest(
        region=region,
        base_image={"id": info.get("imageID", ""), "note": "分步制作，基础镜像信息来自 VM 元数据"},
        builder_vm={
            "instanceId": instance_id,
            "instanceType": info.get("instanceType", ""),
            "publicIP": public_ip,
        },
        install_script_path=getattr(args, "install_script", None),
        output_image={
            "id": image_id,
            "name": args.image_name,
            "minDisk": img_info.get("minDisk"),
            "minCPU": img_info.get("minCPU"),
            "minMemory": img_info.get("minMemory"),
        },
        manifest_dir=manifest_dir,
    )
    print(f"\n📄 构建 manifest 已写出: {manifest_path}")
    print(f"   建议将此文件提交进版本控制，以便追溯镜像构建上下文。")

    if not args.keep_vm:
        print(f"\n删除 VM: {instance_id}...")
        try:
            client.delete_instance(region, instance_id)
            print("VM 已删除")
        except SystemExit:
            print("警告: 删除 VM 失败，请手动清理", file=sys.stderr)
    else:
        print(f"\nVM 保留中: {instance_id}")


def cmd_build(args):
    """一键制作自定义镜像：创建 VM → SSH 安装 → 清理 → 创建镜像 → 删除 VM。"""
    _check_ssh_deps()
    client = _make_client()
    region = args.region
    password = args.password or _generate_password()

    instance_type = args.instance_type
    if not instance_type:
        print("查询最小可用机型...")
        instance_type = _pick_smallest_type(client, region)
        print(f"自动选择机型: {instance_type}")

    base_image_meta: dict = {}
    if args.base_image:
        base_image = args.base_image
        print(f"使用指定基础镜像: {base_image}")
        base_image_meta = {"id": base_image}
    else:
        print("查询 Ubuntu 24.04 官方镜像...")
        images = client.list_images(region, image_type="Official")
        items = images if isinstance(images, list) else images.get("items", images.get("data", []))
        ubuntu = [i for i in items
                  if i.get("osDistribution") == "Ubuntu" and "24.04" in i.get("osVersion", "")]
        if not ubuntu:
            print("错误: 未找到 Ubuntu 24.04 官方镜像", file=sys.stderr)
            sys.exit(1)
        base_image = ubuntu[0]["id"]
        base_image_meta = {
            "id": base_image,
            "name": ubuntu[0].get("name", ""),
            "osDistribution": ubuntu[0].get("osDistribution", ""),
            "osVersion": ubuntu[0].get("osVersion", ""),
        }
        print(f"基础镜像: {base_image} ({ubuntu[0].get('name', '')})")

    builder_name = f"{args.image_name}-builder"
    print(f"\n创建临时 VM: {builder_name} ({instance_type}, {args.disk_size}GB {args.disk_type})...")
    result = client.create_instance(region, instance_type, base_image,
                                    args.disk_type, args.disk_size, args.bandwidth,
                                    password, builder_name)
    instance_id = result["instanceIDs"][0]
    print(f"VM 创建成功: {instance_id}")

    public_ip = ""
    image_id = ""
    img_info: dict = {}
    try:
        public_ip = _wait_vm_running(client, region, instance_id)
        _wait_ssh(public_ip, password, args.ssh_user)
        _ssh_run_script(public_ip, password, args.ssh_user, args.install_script)
        _ssh_cleanup(public_ip, password, args.ssh_user)

        desc = args.image_desc or f"Custom image built from {os.path.basename(args.install_script)}"
        print(f"\n创建镜像: {args.image_name}...")
        img = client.create_image(region, instance_id, args.image_name, desc)
        image_id = img.get("imageID", "")
        print(f"镜像创建中: {image_id}")

        _wait_image_available(client, region, image_id)
        img_info = client.get_image(region, image_id)

        min_disk = img_info.get("minDisk", args.disk_size)
        min_cpu  = img_info.get("minCPU", "?")
        min_mem  = img_info.get("minMemory", "?")

        print(f"\n{'=' * 50}")
        print(f"  镜像制作完成！")
        print(f"{'=' * 50}")
        print(json.dumps(img_info, indent=2, ensure_ascii=False))
        print(f"\n⚠  请在 variables.tf 中同步以下约束，否则创建实例时可能报 400：")
        print(f"   system_disk_size  minimum = {min_disk}")
        print(f"   instance_type     （需满足 CPU ≥ {min_cpu} 核、内存 ≥ {min_mem} GB）")

        # 写出构建 manifest
        manifest_dir = os.path.dirname(os.path.abspath(args.install_script))
        manifest_path = _write_build_manifest(
            region=region,
            base_image=base_image_meta,
            builder_vm={
                "instanceId": instance_id,
                "instanceType": instance_type,
                "diskSize": args.disk_size,
                "diskType": args.disk_type,
                "bandwidth": args.bandwidth,
            },
            install_script_path=args.install_script,
            output_image={
                "id": image_id,
                "name": args.image_name,
                "minDisk": img_info.get("minDisk"),
                "minCPU": img_info.get("minCPU"),
                "minMemory": img_info.get("minMemory"),
            },
            manifest_dir=manifest_dir,
        )
        print(f"\n📄 构建 manifest 已写出: {manifest_path}")
        print(f"   建议将此文件提交进版本控制，以便追溯镜像构建上下文。")

    finally:
        if not args.keep_vm:
            print(f"\n删除临时 VM: {instance_id}...")
            try:
                client.delete_instance(region, instance_id)
                print("VM 已删除")
            except SystemExit:
                print("警告: 删除 VM 失败，请用 vm-cli.py delete-vm 手动清理", file=sys.stderr)
        else:
            print(f"\nVM 保留中:")
            print(f"  Instance ID: {instance_id}")
            print(f"  IP:          {public_ip}")
            print(f"  Password:    {password}")
            print(f"  SSH:         SSHPASS='{password}' sshpass -e ssh {args.ssh_user}@{public_ip}")
            print(f"  删除VM:      python3 vm-cli.py delete-vm --instance-id {instance_id} --region {region}")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="image-cli — LAS 镜像管理与制作工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  # 一键制作镜像（自动选最小机型）
  %(prog)s build --install-script path/to/install.sh \\
           --image-name MyApp-v1.0.0

  # 分步制作：先用 vm-cli.py create-vm 调试，再在此处创建镜像
  %(prog)s create-image --instance-id i-xxxxx \\
           --image-name MyApp-v1.0.0 --password 'VM密码'

  # 列出所有自定义镜像
  %(prog)s list-images --region ap-northeast-1

  # 删除镜像
  %(prog)s delete-image --image-id image-xxxxx --region ap-northeast-1

环境变量:
  QINIU_ACCESS_KEY   七牛 AccessKey（必需）
  QINIU_SECRET_KEY   七牛 SecretKey（必需）""",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # build
    p = sub.add_parser("run-script", help="在已有 VM 上重新执行安装脚本（build 失败后迭代修复用）")
    p.add_argument("--instance-id", required=True, help="VM 实例 ID")
    p.add_argument("--install-script", required=True, help="安装脚本路径")
    p.add_argument("--password", required=True, help="SSH 密码")
    p.add_argument("--region", default="ap-northeast-1", help="区域（默认: ap-northeast-1）")
    p.add_argument("--ssh-user", default="root", help="SSH 用户（默认: root）")

    p = sub.add_parser("get-image", help="查询单个镜像详情")
    p.add_argument("--image-id", required=True, help="镜像 ID")
    p.add_argument("--region", default="ap-northeast-1", help="区域（默认: ap-northeast-1）")

    p = sub.add_parser("build", help="一键制作自定义镜像（VM→安装→镜像→删除VM）",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--install-script", required=True,
                   help="安装脚本路径（上传到 VM 以 root 执行）")
    p.add_argument("--image-name", required=True, help="镜像名称")
    p.add_argument("--image-desc", help="镜像描述")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")
    p.add_argument("--instance-type", help="VM 规格 (默认: 自动选择最小可用机型)")
    p.add_argument("--disk-type", default="cloud.ssd", choices=["local.ssd", "cloud.ssd"],
                   help="磁盘类型 (默认: cloud.ssd)")
    p.add_argument("--disk-size", type=int, default=20, help="系统盘大小 GB，范围 20-500（默认: 20）")
    p.add_argument("--bandwidth", type=int, default=100, choices=[50, 100, 200],
                   help="峰值带宽 Mbps，可选 50/100/200 (默认: 100)")
    p.add_argument("--base-image", help="基础镜像 ID (默认: 自动查询 Ubuntu 24.04)")
    p.add_argument("--password", help="VM 密码 (默认: 随机生成)")
    p.add_argument("--ssh-user", default="root", help="SSH 用户名 (默认: root)")
    p.add_argument("--keep-vm", action="store_true", help="完成后保留 VM 不删除")

    # create-image
    p = sub.add_parser("create-image", help="从已有 VM 创建镜像（配合 vm-cli.py create-vm）",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--instance-id", required=True, help="VM 实例 ID")
    p.add_argument("--image-name", required=True, help="镜像名称")
    p.add_argument("--image-desc", help="镜像描述")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")
    p.add_argument("--password", help="VM 密码（SSH 清理用，--skip-cleanup 时不需要）")
    p.add_argument("--ssh-user", default="root", help="SSH 用户名 (默认: root)")
    p.add_argument("--skip-cleanup", action="store_true", help="跳过 SSH 清理（已手动清理时使用）")
    p.add_argument("--keep-vm", action="store_true", help="镜像创建后保留 VM 不删除")

    # list-images
    p = sub.add_parser("list-images", help="列出镜像")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")
    p.add_argument("--type", default="Custom", choices=["Custom", "CustomPublic", "Official"],
                   help="镜像类型 (默认: Custom)")
    p.add_argument("--name", default="", help="按名称过滤（模糊匹配）")

    # delete-image
    p = sub.add_parser("delete-image", help="删除镜像")
    p.add_argument("--image-id", required=True, help="镜像 ID")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")

    # update-image
    p = sub.add_parser("update-image", help="更新镜像元信息（名称/描述/状态/公开等）")
    p.add_argument("--image-id", required=True, help="镜像 ID")
    p.add_argument("--region", default="ap-northeast-1", help="区域 (默认: ap-northeast-1)")
    p.add_argument("--name", default="", help="新名称（只含字母/数字/短划线/点，2-60字符）")
    p.add_argument("--desc", default=None, help="新描述（最大 100 UTF8 字符）")
    p.add_argument("--state", choices=["Available", "Deprecated", "Disabled"],
                   help="镜像状态（Available/Deprecated/Disabled）")
    p.add_argument("--public", type=lambda x: x.lower() == "true", default=None,
                   metavar="true|false", help="是否公开镜像")
    p.add_argument("--min-cpu", type=int, dest="min_cpu", help="最小 CPU 核心数（1-256）")
    p.add_argument("--min-memory", type=float, dest="min_memory", help="最小内存 GiB（1-2048）")
    p.add_argument("--min-disk", type=int, dest="min_disk", help="最小磁盘 GiB")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "build":         cmd_build,
        "run-script":    cmd_run_script,
        "get-image":     cmd_get_image,
        "create-image":  cmd_create_image,
        "update-image":  cmd_update_image,
        "list-images":   cmd_list_images,
        "delete-image":  cmd_delete_image,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
