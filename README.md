# EasyTier + Clash 共存方案（WireGuard VPN Portal）

解决 Android/iOS 手机上**只能开一个 VPN** 的限制，让 EasyTier 组网和 Clash 翻墙同时工作。

## 问题背景

手机系统（Android/iOS）同一时间只允许一个 VPN 运行。当你同时需要：

- **EasyTier**：虚拟组网，访问内网设备
- **Clash 系代理**：科学上网

两者无法同时开启 TUN 模式，必须来回切换，很麻烦。

### 为什么不能在手机上同时跑？

经过实际测试，在 iOS 上即使 EasyTier 切换为「无 TUN 模式 + SOCKS5」，也存在两个致命问题：

1. **iOS 后台挂起**：切到后台几秒后 EasyTier 被系统挂起，端口不再响应
2. **组网被干扰**：Stash 的 VPN 隧道会拦截 EasyTier 自身的组网通信，导致 EasyTier 根本无法加入网络

因此，**手机上不能运行 EasyTier**，需要一台中转设备。

## 为什么选择 WireGuard

这个方案的早期版本用 EasyTier 的 SOCKS5 代理实现中转。SOCKS5 能用，但有一个根本缺陷：**每建立一条 TCP 连接，都要多走一次 SOCKS5 握手，耗时约 520ms**。手机浏览器加载一个页面通常发出 30 个以上的资源请求，握手延迟全部叠加，页面加载白白多出 2-3 秒。

更麻烦的是，SOCKS5 不支持认证，任何知道 VPS IP 和端口的人都能进来，只能靠防火墙白名单勉强保住安全性。

WireGuard 解决了这两个问题：

- **L3 隧道，连接透明传输**：WireGuard 工作在网络层，TCP 连接在隧道中直接传输，HTTP Keep-Alive 天然生效，不需要额外握手
- **内置加密和密钥认证**：没有对应私钥就无法接入，安全性比 SOCKS5 高一个量级

一句话对比：**SOCKS5 是中介，WireGuard 是专线**。

EasyTier 的 `--vpn-portal` 功能正好实现了这个专线：它在 VPS 上开放一个 WireGuard 入口，Clash 客户端直接用 WireGuard 代理节点接入，所有虚拟网段流量在隧道内透明传输，延迟和体验都接近原生。

## 解决方案架构

```
iPhone / Android（Stash / FlClash）
  │
  │  访问 10.126.126.x
  │  匹配覆写规则 → 走 Proxy-EasyTier（WireGuard）
  │
  ▼
VPS（YOUR_VPS_IP:11013/udp）
  │  EasyTier WireGuard VPN Portal
  │  Docker 部署，24小时在线
  │
  ▼
EasyTier 虚拟网络（10.126.126.0/24）
  ├── Mac（10.126.126.2）
  ├── VPS（DHCP 自动分配）
  └── 其他设备...
```

**核心原理**：

- VPS 上用 Docker 运行 EasyTier，加入你的虚拟网络，并开启 WireGuard VPN Portal
- 手机上的 Clash 客户端通过覆写规则，将虚拟网段流量走 WireGuard 代理节点到达 VPS
- 手机**完全不需要安装或运行 EasyTier**

## VPS 部署（Docker）

### 1. 准备环境

确保 VPS 已安装 Docker 和 Docker Compose：

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
```

### 2. 部署 EasyTier

```bash
# 克隆仓库
git clone https://github.com/1023530810/easytier-clash-override.git
cd easytier-clash-override/docker

# 配置网络凭据
cp .env.example .env
nano .env  # 填入你的 EasyTier 网络名和密码
```

编辑 `.env` 文件：

```bash
# 必须和你 Mac/其他设备上的 EasyTier 使用相同的网络名和密码
ET_NETWORK_NAME=你的网络名称
ET_NETWORK_SECRET=你的网络密码
```

### 3. 修改中继服务器（可选）

编辑 `docker-compose.yml` 中的 `-p` 参数，替换为你实际使用的公共中继服务器：

```yaml
command: >
  -d
  --vpn-portal wg://0.0.0.0:11013/10.14.14.0/24
  --hostname vps-gateway
  -p tcp://8.148.29.206:11010        # ← 替换为你的中继服务器
  -p tcp://160.202.238.39:20665
```

`--vpn-portal` 参数说明：

- `wg://0.0.0.0:11013`：在所有网卡的 UDP 11013 端口开放 WireGuard 入口
- `/10.14.14.0/24`：为接入客户端分配的 VPN Portal 地址段

> 可以用 `scripts/fetch_servers.py --raw` 获取最新的公共服务器列表。

### 4. 启动服务

```bash
docker compose up -d
```

### 5. 验证

```bash
# 查看日志，确认组网成功
docker compose logs -f

# 进入容器检查节点状态
docker exec -it easytier easytier-cli peer
docker exec -it easytier easytier-cli route
```

在日志中应该能看到其他节点（如你的 Mac）出现在 peer 列表中。

### 6. 防火墙配置

WireGuard 使用 UDP 协议，需要开放 UDP 11013 端口：

```bash
# ufw（推荐）
sudo ufw allow 11013/udp

# 或 iptables
sudo iptables -A INPUT -p udp --dport 11013 -j ACCEPT

# 持久化 iptables 规则
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

与旧版 SOCKS5 方案不同，WireGuard 内置密钥认证，不需要额外限制来源 IP。没有对应私钥的连接会直接被忽略。

### Web Console（自建，可选）

在浏览器查看所有组网设备及其 IP，无需 SSH。控制台随 docker compose 一起启动，无需依赖官网服务。

1. 启动服务后，打开 `http://你的VPS公网IP:11211`
2. 点击 `Register` 注册一个账号
3. 将注册的用户名填入 `.env`：

```bash
ET_WEB_USERNAME=你注册的用户名
```

4. 重启容器让 EasyTier 节点连接控制台：

```bash
docker compose up -d
```

5. 登录 Web Console，点击设备即可查看虚拟 IP、在线状态、延迟等信息

> Docker 环境下已通过 `--machine-id` 固定设备标识，重启容器不会丢失配置。
> Web Console 数据持久化在 `docker/web-data/` 目录。

## 获取 WireGuard 客户端配置

VPS 部署并组网成功后，执行以下命令获取 WireGuard 客户端接入信息：

```bash
docker exec -it easytier easytier-cli vpn-portal
```

输出示例：

```
portal_name: wg://0.0.0.0:11013/10.14.14.0/24
server_public_key: aBcDeFgH...（base64 公钥）
connected clients: []
my_client_config:
[Interface]
PrivateKey = xYzAbC...（客户端私钥）
Address = 10.14.14.1/24

[Peer]
PublicKey = aBcDeFgH...（服务端公钥）
Endpoint = <your-endpoint>:11013
AllowedIPs = 10.14.14.0/24, 10.126.126.0/24
PersistentKeepalive = 25
```

将上述信息对应填入 Clash 的 WireGuard 代理配置：

| vpn-portal 输出 | Clash 配置字段 |
|-----------------|----------------|
| `PrivateKey` | `private-key` |
| `PublicKey`（Peer 段） | `public-key` |
| VPS 公网 IP | `server` |
| `11013` | `port` |
| `Address` 中的 IP | `ip` |

**每台设备需要使用不同的 `ip`**（如第一台 `10.14.14.1`，第二台 `10.14.14.2`，第三台 `10.14.14.3`），否则会产生 IP 冲突。目前需要手动为每台设备分配不同 IP，填入对应客户端配置文件。

## 客户端配置

三种客户端配置均已预置 WireGuard 代理节点模板，填入从 `easytier-cli vpn-portal` 获取的密钥后即可使用。

### Stash（iOS）

覆写文件默认使用 IP `10.14.14.1`（第一台设备）。

1. 打开 Stash → 设置 → 覆写 → 点击右上角 `+`
2. 选择「添加配置链接」，输入：

```
https://raw.githubusercontent.com/1023530810/easytier-clash-override/main/stash/easytier.stoverride
```

3. 在覆写中将 `YOUR_VPS_IP`、`YOUR_PRIVATE_KEY`、`YOUR_PUBLIC_KEY` 替换为实际值
4. 确保覆写开关已打开，重新连接 VPN

Stash 的数组合并规则会自动将配置**追加**到你的订阅前面，不会覆盖机场节点。

### FlClash（Android）

覆写脚本默认使用 IP `10.14.14.2`（第二台设备）。

1. 复制 `flclash/easytier-override.js` 的内容
2. 将脚本中的 `YOUR_VPS_IP`、`YOUR_PRIVATE_KEY`、`YOUR_PUBLIC_KEY` 替换为实际值
3. 打开 FlClash → 配置页 → 右上角齿轮/脚本图标
4. 删除默认脚本内容，粘贴修改后的脚本
5. 在 订阅 → 三个点 → 覆写 → 开启覆写开关
6. 重新连接 VPN

### FlClash/Clash（Mac）

Mac 已原生接入 EasyTier，不需要 WireGuard 代理。使用 `flclash/easytier-override-mac.js`，将 EasyTier 网段走 DIRECT。

1. 复制 `flclash/easytier-override-mac.js` 的内容
2. 将内容贴入 Clash 的覆写脚本编辑框
3. 开启覆写开关、重连 VPN

> Mac 版无需修改任何占位符，也不占用 VPN Portal IP。
### 独立配置（无订阅）

`standalone/easytier-standalone.yaml` 默认使用 IP `10.14.14.3`（第三台设备）。

如果你没有机场订阅，将文件中的三个占位值替换为实际密钥后，直接导入 Clash 客户端即可。需要手动添加你的翻墙代理节点。

## 自定义修改

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `server` | `YOUR_VPS_IP` | VPS 公网 IP，改成你自己的 VPS |
| `port` | `11013` | WireGuard UDP 端口 |
| 规则网段 | `10.126.126.0/24` | EasyTier 虚拟网段，按你的实际网段调整 |
| `ET_WEB_USERNAME` | （空） | 自建 Web Console 用户名，首次启动后在 `http://VPS:11211` 注册 |

> 只拦截 EasyTier 虚拟网段（如 `10.126.126.0/24`），**不要**拦截 `192.168.0.0/16` 等局域网网段，否则会导致本地网络访问全部失败。

## 注意事项

- **测速失败是正常的**：WireGuard 代理只能访问虚拟网络内的设备，不是通用互联网代理，Clash 测速访问公网 URL 会超时
- **WireGuard 吞吐量略低于原生**：移动端（Stash/FlClash）使用用户空间 WireGuard 实现，加密/解密不走内核，吞吐量有一定损耗，但对内网访问场景完全够用
- **ICMP/Ping 不可用**：通过 Clash WireGuard 代理时，ICMP 协议无法传输，不能用 ping 测试连通性。请用 SSH、curl 等 TCP 工具验证
- VPS 需要保持 Docker 容器运行，建议配置 `restart: unless-stopped`（已默认开启）

## 服务器列表抓取工具

`scripts/fetch_servers.py` 用于自动抓取 [Astral 社区公共服务器列表](https://astral.fan/server-config/server-list/)，将所有服务器转换为 `tcp://` 或 `udp://` 格式，并自动检测服务器变更。

### 环境要求

- Python 3.9+（无需安装额外依赖，仅使用标准库）

### 使用方法

```bash
# 完整模式（默认）
# 显示变更报告 + 服务器详情 + URI 汇总
python3 scripts/fetch_servers.py

# 变更检测模式
# 仅显示新增/删除的服务器，不显示完整列表
python3 scripts/fetch_servers.py --diff

# 纯输出模式
# 仅输出 URI 列表，方便复制到 EasyTier 配置或 docker-compose.yml
python3 scripts/fetch_servers.py --raw

# 自动更新 docker-compose.yml 中的 -p 参数
python3 scripts/fetch_servers.py --update-compose
```

### 配合定时任务使用

```bash
# 每天早上 8 点检查一次，将变更写入日志
0 8 * * * cd /path/to/easytier-clash-override && python3 scripts/fetch_servers.py --diff >> /tmp/easytier-servers.log 2>&1
```

## 常见问题

### Q: 手机上需要安装 EasyTier 吗？

**不需要。** VPS 作为中转，手机通过 Clash WireGuard 代理节点访问 EasyTier 虚拟网络，完全不需要在手机上运行 EasyTier。

### Q: 测速显示 Proxy-EasyTier 超时/失败？

**正常。** WireGuard 代理只能访问虚拟网络（10.126.126.0/24），不能访问公网测速 URL。只要能通过 SSH/curl 访问虚拟网络内的设备就说明工作正常。

### Q: 为什么不在手机上直接跑 EasyTier？

iOS 上 EasyTier 切后台后会被系统挂起，且 Stash 的 VPN 隧道会干扰 EasyTier 的组网通信。详见[问题背景](#为什么不能在手机上同时跑)。

### Q: 多台设备如何分配 IP？

每台设备需要使用不同的 `ip`（VPN Portal 地址段 `10.14.14.0/24` 内的不同地址）。目前三套客户端配置分别预置了：

- Stash（iOS）：`10.14.14.1`
- FlClash（Android）：`10.14.14.2`
- standalone：`10.14.14.3`

如果你有多台同类型设备，复制配置文件并手动修改 `ip` 字段即可。

### Q: WireGuard 需要限制防火墙来源 IP 吗？

不需要。WireGuard 内置密钥认证，没有对应私钥的握手请求会直接被丢弃，不会建立连接。开放 UDP 11013 端口就够了。

### Q: `easytier-cli vpn-portal` 没有输出客户端配置？

确认 EasyTier 已成功加入网络（`easytier-cli peer` 能看到其他节点）。如果容器刚启动，等待 10-20 秒再试。

## 参考资料

- [EasyTier VPN Portal 文档](https://easytier.cn/guide/network/vpn-portal.html)
- [EasyTier Web Console 自建文档](https://easytier.cn/en/guide/network/web-console.html#self-hosted-web-console)
- [EasyTier GitHub](https://github.com/EasyTier/EasyTier)
- [EasyTier Docker 部署文档](https://easytier.cn/en/guide/installation.html)
- [Mihomo WireGuard 代理文档](https://wiki.metacubex.one/en/config/proxies/wg/)
- [Stash 覆写文档](https://stash.wiki/configuration/override)
- [FlClash 覆写脚本教程](https://github.com/chen08209/FlClash/issues/1510)
- [Astral 社区服务器列表](https://astral.fan/server-config/server-list/)

## License

MIT
