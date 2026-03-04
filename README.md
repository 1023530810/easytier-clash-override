# EasyTier + Clash 共存方案

解决 Android/iOS 手机上**只能开一个 VPN** 的限制，让 EasyTier 组网和 Clash 翻墙同时工作。

## 问题背景

手机系统（Android/iOS）同一时间只允许一个 VPN 运行。当你同时需要：
- **EasyTier**：虚拟组网，访问内网设备
- **Clash 系代理**：科学上网

两者无法同时开启 TUN 模式，必须来回切换，非常麻烦。

### 为什么不能在手机上同时跑？

经过实际测试，在 iOS 上即使 EasyTier 切换为"无 TUN 模式 + SOCKS5"，也存在两个致命问题：

1. **iOS 后台挂起**：切到后台几秒后 EasyTier 被系统挂起，SOCKS5 端口不再响应
2. **组网被干扰**：Stash 的 VPN 隧道会拦截 EasyTier 自身的组网通信，导致 EasyTier 根本无法加入网络

因此，**手机上不能运行 EasyTier**，需要一台中转设备。

## 解决方案：VPS 中转

```
iPhone / Android（Stash / FlClash）
  │
  │  访问 10.126.126.x
  │  匹配覆写规则 → 走 Proxy-EasyTier
  │
  ▼
VPS（YOUR_VPS_IP:15555）
  │  EasyTier SOCKS5 代理
  │  Docker 部署，24小时在线
  │
  ▼
EasyTier 虚拟网络（10.126.126.0/24）
  ├── Mac（10.126.126.2）
  ├── VPS（DHCP 自动分配）
  └── 其他设备...
```

**核心原理**：
- VPS 上用 Docker 运行 EasyTier，加入你的虚拟网络，并开启 SOCKS5 代理
- 手机上的 Clash 客户端通过覆写规则，将虚拟网段流量转发到 VPS 的 SOCKS5
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
  --socks5 15555
  --hostname vps-gateway
  -p tcp://8.148.29.206:11010        # ← 替换为你的中继服务器
  -p tcp://160.202.238.39:20665
```

> 💡 可以用 `scripts/fetch_servers.py --raw` 获取最新的公共服务器列表。

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

> 💡 Docker 环境下已通过 `--machine-id` 固定设备标识，重启容器不会丢失配置。
> Web Console 数据持久化在 `docker/web-data/` 目录。

### 6. 安全加固

⚠️ **EasyTier 的 SOCKS5 不支持认证**（无用户名密码），必须用防火墙限制访问。

```bash
# 只允许特定 IP 访问 SOCKS5 端口（推荐）
# 替换 YOUR_IP 为你常用的出口 IP
sudo iptables -A INPUT -p tcp --dport 15555 -s YOUR_IP -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 15555 -j DROP

# 或者，如果你的 IP 经常变化，至少限制为国内 IP 段
# 配合 fail2ban 等工具使用

# 持久化 iptables 规则
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

> ⚠️ SOCKS5 无认证意味着任何知道你 VPS IP 和端口的人都能访问你的 EasyTier 虚拟网络。务必配置防火墙！

## 客户端配置

### Stash（iOS）推荐

1. 打开 Stash → 设置 → 覆写 → 点击右上角 `+`
2. 选择「添加配置链接」，输入：

```
https://raw.githubusercontent.com/1023530810/easytier-clash-override/main/stash/easytier.stoverride
```

3. 确保覆写开关已打开
4. 重新连接 VPN

Stash 的数组合并规则会自动将配置**追加**到你的订阅前面，不会覆盖机场节点。

### FlClash（Android/桌面）

1. 复制 `flclash/easytier-override.js` 的内容
2. 打开 FlClash → 配置页 → 右上角齿轮/脚本图标
3. 删除默认脚本内容，粘贴复制的脚本
4. 在 订阅 → 三个点 → 覆写 → 开启覆写开关
5. 重新连接 VPN

### 独立配置（无订阅）

如果你没有机场订阅，直接使用 `standalone/easytier-standalone.yaml` 作为完整配置文件导入 Clash 客户端即可。需要手动添加你的代理节点。

## 配置文件说明

```
├── docker/                          # VPS Docker 部署
│   ├── docker-compose.yml           # Docker Compose 配置（含 Web Console）
│   ├── .env.example                 # 环境变量模板
│   ├── data/                        # EasyTier 节点数据
│   └── web-data/                    # Web Console 持久化数据
├── stash/                           # iOS Stash 客户端
│   └── easytier.stoverride          # Stash 覆写文件
├── flclash/                         # FlClash 客户端（Android/桌面）
│   └── easytier-override.js         # FlClash JavaScript 覆写脚本
├── standalone/                      # 通用独立配置
│   └── easytier-standalone.yaml     # 完整 Clash YAML（无订阅时使用）
└── scripts/                         # 工具脚本
    └── fetch_servers.py             # 公共服务器列表抓取与变更检测
```

## 自定义修改

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `server` | `YOUR_VPS_IP` | VPS 公网 IP，改成你自己的 VPS |
| `port` | `15555` | VPS 上 EasyTier 的 SOCKS5 端口 |
| 规则网段 | `10.126.126.0/24` | EasyTier 虚拟网段，按你的实际网段调整 |
| `ET_WEB_USERNAME` | （空） | 自建 Web Console 用户名，首次启动后在 `http://VPS:11211` 注册 |

> ⚠️ 只拦截 EasyTier 虚拟网段（如 `10.126.126.0/24`），**不要**拦截 `192.168.0.0/16` 等局域网网段，否则会导致本地网络访问全部失败。

## 注意事项

- **测速失败是正常的**：EasyTier SOCKS5 只能访问虚拟网络内的设备，不是通用互联网代理，Clash 测速访问公网 URL 会超时
- **TCP 通信**正常工作（SSH、HTTP、远程桌面等）
- **UDP 通信**取决于 EasyTier 的 SOCKS5 是否支持 UDP ASSOCIATE
- **ICMP/Ping 不可用**：SOCKS5 不支持 ICMP 协议，不能用 ping 测试连通性。请用 SSH、curl 等 TCP 工具测试
- VPS 需要保持 Docker 容器运行，建议配置 `restart: unless-stopped`

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
```

### 配合定时任务使用

```bash
# 每天早上 8 点检查一次，将变更写入日志
0 8 * * * cd /path/to/easytier-clash-override && python3 scripts/fetch_servers.py --diff >> /tmp/easytier-servers.log 2>&1
```

## 常见问题

### Q: 手机上需要安装 EasyTier 吗？

**不需要。** VPS 作为中转，手机通过 Clash 覆写规则访问 EasyTier 虚拟网络，完全不需要在手机上运行 EasyTier。

### Q: 测速显示 Proxy-EasyTier 超时/失败？

**正常。** EasyTier SOCKS5 只能访问虚拟网络（10.126.126.0/24），不能访问公网测速 URL。只要能通过 SSH/curl 访问虚拟网络内的设备就说明工作正常。

### Q: 为什么不在手机上直接跑 EasyTier？

iOS 上 EasyTier 切后台后会被系统挂起，SOCKS5 停止响应。且 Stash 的 VPN 隧道会干扰 EasyTier 的组网通信。详见 [问题背景](#为什么不能在手机上同时跑)。

### Q: VPS 的 SOCKS5 安全吗？

EasyTier 的 SOCKS5 **不支持认证**。务必配置防火墙限制访问端口。详见 [安全加固](#6-安全加固)。

## 参考资料

- [EasyTier Web Console 自建文档](https://easytier.cn/en/guide/network/web-console.html#self-hosted-web-console)
- [EasyTier GitHub](https://github.com/EasyTier/EasyTier)
- [EasyTier Docker 部署文档](https://easytier.cn/en/guide/installation.html)
- [EasyTier SOCKS5 文档](https://easytier.cn/en/guide/network/socks5.html)
- [EasyTier Issue #1825](https://github.com/EasyTier/EasyTier/issues/1825)
- [Stash 覆写文档](https://stash.wiki/configuration/override)
- [FlClash 覆写脚本教程](https://github.com/chen08209/FlClash/issues/1510)
- [Astral 社区服务器列表](https://astral.fan/server-config/server-list/)

## License

MIT
