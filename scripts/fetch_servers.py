#!/usr/bin/env python3
"""
EasyTier 公共服务器列表抓取工具

从 https://astral.fan/server-config/server-list/ 抓取所有可用服务器，
转换为 tcp:// 或 udp:// 格式，并自动检测新增/删除的服务器。

用法：
    python3 fetch_servers.py                    # 抓取并显示所有服务器
    python3 fetch_servers.py --diff             # 仅显示变更（新增/删除）
    python3 fetch_servers.py --raw              # 仅输出 URI 列表（方便复制）
    python3 fetch_servers.py --update-compose   # 自动更新 docker-compose.yml 的中继服务器
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime

URL = "https://astral.fan/server-config/server-list/"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".servers_state.json")
COMPOSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docker", "docker-compose.yml")


def fetch_page(url: str) -> str:
    """抓取页面 HTML 内容"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; EasyTierServerFetcher/1.0)"
    })
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        return resp.read().decode("utf-8")


def parse_servers(html: str) -> list[dict]:
    """
    解析 HTML，提取服务器列表。
    每个服务器格式：
      <strong>名称/提供商/中转/协议</strong> 地址: <code>host:port</code>
    """
    servers = []

    # 匹配 <strong>...</strong> 后跟 <code>...</code> 的模式
    pattern = re.compile(
        r"<strong>(.*?)</strong>.*?地址:\s*<code>(.*?)</code>",
        re.DOTALL
    )

    for match in pattern.finditer(html):
        info = match.group(1).strip()
        address = match.group(2).strip()

        # 从 info 中解析字段：名称/提供商/中转能力/协议
        parts = [p.strip() for p in info.split("/")]

        name = parts[0] if len(parts) > 0 else "未知"
        provider = parts[1] if len(parts) > 1 else "未知"
        relay = parts[2] if len(parts) > 2 else "未知"

        # 协议可能跨多个部分（如 "TCP/UDP" 被 split 成两段）
        # 将第3个字段之后的所有部分拼接起来判断协议
        proto_str = "/".join(parts[3:]).upper() if len(parts) > 3 else "TCP"

        # 确定协议列表
        protocols = []
        if "TCP" in proto_str:
            protocols.append("tcp")
        if "UDP" in proto_str:
            protocols.append("udp")
        if not protocols:
            protocols.append("tcp")  # 默认 TCP

        servers.append({
            "name": name,
            "provider": provider,
            "relay": relay,
            "protocols": protocols,
            "address": address,
        })

    return servers


def to_uri(server: dict) -> list[str]:
    """将服务器信息转换为 protocol://address 格式"""
    uris = []
    for proto in server["protocols"]:
        uris.append(f"{proto}://{server['address']}")
    return uris


def load_state() -> dict:
    """加载上次保存的状态"""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(servers: list[dict]):
    """保存当前状态"""
    state = {
        "updated_at": datetime.now().isoformat(),
        "servers": {s["address"]: s for s in servers},
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def diff_servers(old_state: dict, current_servers: list[dict]) -> tuple[list[dict], list[dict]]:
    """比较新旧服务器列表，返回 (新增列表, 删除列表)"""
    old_servers = old_state.get("servers", {})
    old_addrs = set(old_servers.keys())
    new_addrs = set(s["address"] for s in current_servers)

    added = [s for s in current_servers if s["address"] not in old_addrs]
    removed = [old_servers[addr] for addr in old_addrs - new_addrs]

    return added, removed


def print_server_table(servers: list[dict]):
    """以表格形式打印服务器列表"""
    print(f"\n{'─' * 70}")
    print(f"  📡 EasyTier 公共服务器列表（共 {len(servers)} 个）")
    print(f"  🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─' * 70}\n")

    for i, s in enumerate(servers, 1):
        uris = to_uri(s)
        relay_icon = "❌" if "不可中转" in s["relay"] else ("✅" if "可中转" in s["relay"] else "❓")
        print(f"  [{i:2d}] {s['name']} ({s['provider']})")
        print(f"       中转: {relay_icon} {s['relay']}")
        for uri in uris:
            print(f"       👉 {uri}")
        print()


def print_diff(added: list[dict], removed: list[dict], old_state: dict):
    """打印变更信息"""
    last_update = old_state.get("updated_at", "未知")

    print(f"\n{'─' * 70}")
    print(f"  🔄 服务器变更报告")
    print(f"  📅 上次检查：{last_update}")
    print(f"  🕐 本次检查：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─' * 70}\n")

    if not added and not removed:
        print("  ✅ 无变更，服务器列表与上次一致。\n")
        return

    if added:
        print(f"  🆕 新增服务器（{len(added)} 个）：")
        for s in added:
            for uri in to_uri(s):
                print(f"     + {uri}  ← {s['name']} ({s['provider']})")
        print()

    if removed:
        print(f"  🗑️  已删除服务器（{len(removed)} 个）：")
        for s in removed:
            for uri in to_uri(s):
                print(f"     - {uri}  ← {s['name']} ({s['provider']})")
        print()


def update_compose(servers: list[dict], compose_path: str = None):
    """更新 docker-compose.yml 中的 -p 中继服务器列表"""
    path = compose_path or COMPOSE_FILE
    path = os.path.abspath(path)

    if not os.path.exists(path):
        print(f"  ❌ docker-compose.yml 不存在：{path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 收集所有 TCP URI（docker-compose 连接用 TCP）
    tcp_uris = []
    for s in servers:
        for uri in to_uri(s):
            if uri.startswith("tcp://"):
                tcp_uris.append(uri)

    # 找到 -p 行的起始和结束位置
    first_p_idx = None
    last_p_idx = None
    indent = "      "  # 默认 6 空格缩进

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if re.match(r"^\s+-p\s+", stripped):
            if first_p_idx is None:
                first_p_idx = i
                # 提取实际缩进
                indent = re.match(r"^(\s+)", line).group(1)
            last_p_idx = i

    if first_p_idx is None:
        # 没找到 -p 行，在 command 块末尾添加
        for i, line in enumerate(lines):
            if "--hostname" in line:
                first_p_idx = i + 1
                last_p_idx = i  # 没有现有 -p 行
                indent = re.match(r"^(\s+)", line).group(1)
                break

    if first_p_idx is None:
        print("  ❌ 无法定位 docker-compose.yml 中的 command 块", file=sys.stderr)
        sys.exit(1)

    # 构建新的 -p 行
    new_p_lines = [f"{indent}-p {uri}\n" for uri in tcp_uris]

    # 替换旧的 -p 行
    new_lines = lines[:first_p_idx] + new_p_lines + lines[last_p_idx + 1:]

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"\n{'─' * 70}")
    print(f"  🔧 docker-compose.yml 已更新")
    print(f"  📄 文件：{path}")
    print(f"  📡 中继服务器：{len(tcp_uris)} 个 TCP 节点")
    print(f"{'─' * 70}\n")

    for uri in tcp_uris:
        print(f"  -p {uri}")
    print()

    print("  💡 运行以下命令使更新生效：")
    print("     cd docker && docker compose up -d\n")


def main():
    args = set(sys.argv[1:])
    diff_mode = "--diff" in args
    raw_mode = "--raw" in args
    compose_mode = "--update-compose" in args

    try:
        html = fetch_page(URL)
    except Exception as e:
        print(f"❌ 抓取失败：{e}", file=sys.stderr)
        sys.exit(1)

    servers = parse_servers(html)

    if not servers:
        print("❌ 未解析到任何服务器，页面结构可能已变更。", file=sys.stderr)
        sys.exit(1)

    # 更新 docker-compose.yml 模式
    if compose_mode:
        update_compose(servers)
        save_state(servers)
        return

    # 纯输出模式：仅打印 URI
    if raw_mode:
        for s in servers:
            for uri in to_uri(s):
                print(uri)
        save_state(servers)
        return

    # 加载旧状态
    old_state = load_state()

    if old_state:
        added, removed = diff_servers(old_state, servers)
        print_diff(added, removed, old_state)

        if not diff_mode:
            print_server_table(servers)
    else:
        print("  ℹ️  首次运行，无历史数据可比较。\n")
        print_server_table(servers)

    # 保存当前状态
    save_state(servers)

    # 输出可复制的 URI 汇总
    print(f"{'─' * 70}")
    print("  📋 可直接复制的 URI 列表：")
    print(f"{'─' * 70}\n")
    for s in servers:
        for uri in to_uri(s):
            print(f"  {uri}")
    print()


if __name__ == "__main__":
    main()
