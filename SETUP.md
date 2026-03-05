# 快速上手操作指南

> 本文档面向**首次部署**的用户，按实际操作顺序排列，跟着走即可完成全部配置。

---

## 你需要准备什么

| 角色 | 要求 |
|------|------|
| **VPS**（必须） | 有公网 IP，能装 Docker，推荐 Ubuntu 22.04 |
| **Mac / 电脑**（已有） | 已运行 EasyTier 并加入你的虚拟网络 |
| **手机**（目标） | iOS 用 Stash，Android 用 FlClash |

---

## 第一步：VPS 部署（一次性，约 10 分钟）

### 1.1 安装 Docker

SSH 登录 VPS，执行：

```bash
curl -fsSL https://get.docker.com | sh
```

### 1.2 克隆本仓库

```bash
git clone https://github.com/1023530810/easytier-clash-override.git
cd easytier-clash-override/docker
```

### 1.3 配置网络凭据

```bash
cp .env.example .env
nano .env
```

填入**和你 Mac 上 EasyTier 完全相同**的网络名和密码：

```bash
ET_NETWORK_NAME=你的网络名称      # 必须和 Mac 上一致
ET_NETWORK_SECRET=你的网络密码    # 必须和 Mac 上一致
ET_WEB_USERNAME=                  # 先留空，后面注册完再填
```

> 按 `Ctrl+O` 保存，`Ctrl+X` 退出。

### 1.4 填写 VPS 公网 IP

打开 `docker-compose.yml`，找到并替换 `YOUR_VPS_IP`：

```bash
nano docker-compose.yml
```

找到这一行：

```yaml
--api-host http://YOUR_VPS_IP:11211
```

改为你的实际公网 IP，例如：

```yaml
--api-host http://1.2.3.4:11211
```

保存退出。

### 1.5 开放防火墙端口

```bash
# WireGuard 端口（手机连接必须）
sudo ufw allow 11013/udp

# Web 控制台端口（可选，浏览器查看状态用）
sudo ufw allow 11211/tcp
```

**重要**：如果你用的是云服务商的安全组（阿里云、腾讯云、AWS 等），还需要在云控制台里单独放行 **UDP 11013**，这步容易漏掉。

### 1.6 启动服务

```bash
docker compose up -d
```

等待 10-20 秒，验证是否组网成功：

```bash
# 查看日志（看到 Mac 节点信息说明成功，Ctrl+C 退出）
docker compose logs -f

# 查看节点列表（应该能看到你的 Mac）
docker exec -it easytier easytier-cli peer
```

`peer` 列表里能看到你的 Mac 节点，说明 VPS 已成功加入 EasyTier 虚拟网络。

---

## 第二步：获取 WireGuard 客户端密钥

VPS 组网成功后，执行以下命令取出 WireGuard 配置：

```bash
docker exec -it easytier easytier-cli vpn-portal
```

输出示例：

```
portal_name: wg://0.0.0.0:11013/10.14.14.0/24
server_public_key: aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890abcd=

my_client_config:
[Interface]
PrivateKey = xYzAbCdEfGhIjKlMnOpQrStUvWxYz1234567890ab=
Address = 10.14.14.1/24

[Peer]
PublicKey = aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890abcd=
Endpoint = <your-endpoint>:11013
AllowedIPs = 10.14.14.0/24, 10.126.126.0/24
PersistentKeepalive = 25
```

**记录以下三个值，填写客户端配置时用：**

| 从输出中取 | 对应 Clash 配置字段 |
|-----------|-------------------|
| `PrivateKey = ...` 后面那串 | `private-key`（你的私钥，不要给别人） |
| `server_public_key: ...` 那串 | `public-key`（服务端公钥） |
| 你的 VPS 公网 IP | `server` |

> **多台设备需要不同 IP**：每台设备重新执行 `vpn-portal` 命令会生成新的私钥。  
> IP 分配建议：iOS = `10.14.14.1`，Android = `10.14.14.2`，第三台 = `10.14.14.3`。

---

## 第三步：手机配置（选其中一种）

### iOS — Stash

**前提**：已有机场订阅，Stash 正常使用。

1. 打开 Stash → **设置** → **覆写** → 右上角 `+`
2. 选「添加配置链接」，填入：

   ```
   https://raw.githubusercontent.com/1023530810/easytier-clash-override/main/stash/easytier.stoverride
   ```

3. 添加后，点进该覆写 → **编辑**，找到 `proxies` 块，替换占位符：

   ```yaml
   - name: Proxy-EasyTier
     type: wireguard
     server: 1.2.3.4          # ← 改成你的 VPS 公网 IP
     port: 11013
     ip: 10.14.14.1            # ← iOS 设备用 .1
     private-key: xYzAbC...   # ← 粘贴你的 PrivateKey
     public-key: aBcDeF...    # ← 粘贴 server_public_key
     udp: true
     mtu: 1380
     persistent-keepalive: 25
   ```

4. 确保覆写开关**已打开**
5. 重新连接 Stash VPN

---

### Android — FlClash

1. 用文本编辑器打开 `flclash/easytier-override.js`，替换以下三处：

   ```javascript
   server: "YOUR_VPS_IP",         // → 你的 VPS 公网 IP，如 "1.2.3.4"
   "private-key": "YOUR_PRIVATE_KEY",  // → 粘贴 PrivateKey
   "public-key": "YOUR_PUBLIC_KEY",    // → 粘贴 server_public_key
   ```

   `ip: "10.14.14.2"` 是 Android 默认 IP，保持不变即可。

2. 打开 FlClash → **配置页** → 右上角**脚本图标**
3. 清空默认内容，粘贴修改好的脚本全文
4. 订阅 → 三个点 → **覆写** → 打开覆写开关
5. 重新连接

---

### 无订阅 — standalone 配置

适合没有机场订阅、只想访问 EasyTier 内网的情况。

1. 打开 `standalone/easytier-standalone.yaml`，替换三处占位符：

   ```yaml
   server: YOUR_VPS_IP          # → 你的 VPS 公网 IP
   private-key: YOUR_PRIVATE_KEY  # → 粘贴 PrivateKey
   public-key: YOUR_PUBLIC_KEY    # → 粘贴 server_public_key
   ```

   `ip: 10.14.14.3` 保持不变（standalone 默认用 .3）。

2. 将修改好的文件导入 Clash 客户端（ClashX / Clash for Windows / Mihomo Party 等）。

---

## 第四步：验证连通性

> **不能用 ping！** WireGuard 通过 Clash 代理时 ICMP 不可用，改用 TCP 工具验证。

```bash
# 从手机 SSH 连接你的 Mac（需要 Mac 开启远程登录）
ssh 用户名@10.126.126.2    # 换成你 Mac 的 EasyTier 虚拟 IP

# 或者 curl 访问 Mac 上跑的任意 HTTP 服务
curl http://10.126.126.2:端口
```

能连上，说明整个链路通了。

---

## 关键信息速查表（填好后备用）

```
VPS 公网 IP:           _______________
EasyTier 网络名:       _______________
EasyTier 密码:         _______________

WireGuard 端口:        UDP 11013
VPN Portal 子网:       10.14.14.0/24
EasyTier 虚拟网段:     10.126.126.0/24

iOS（Stash）IP:        10.14.14.1
Android（FlClash）IP:  10.14.14.2
standalone IP:         10.14.14.3

服务端公钥（server_public_key）:
_______________________________________________

iOS 私钥（PrivateKey）:
_______________________________________________

Android 私钥（PrivateKey）:
_______________________________________________
```

> 私钥只存在本地，不要上传到 git 或分享给他人。

---

## 常见问题

| 现象 | 原因 | 解决方法 |
|------|------|---------|
| `vpn-portal` 命令无输出或报错 | VPS 还没成功组网 | 先确认 `easytier-cli peer` 能看到其他节点 |
| 手机连上但访问 `10.126.126.x` 超时 | 防火墙没放 UDP 11013 | 检查 `ufw` 状态 + 云服务商安全组 |
| Stash 测速 Proxy-EasyTier 超时 | 正常现象 | WireGuard 代理只通内网，不是公网代理 |
| 两台手机互相干扰 / 断线 | 两台设备使用了相同的 `ip` 字段 | 第二台改成 `10.14.14.2`，第三台改 `.3` |
| VPS 重启后无法访问 | Docker 服务未随系统启动 | `systemctl enable docker` |
| `peer` 列表看不到 Mac | 网络名或密码填错 | 检查 `.env` 和 Mac 上的 EasyTier 配置是否一致 |
