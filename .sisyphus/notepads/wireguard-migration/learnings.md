1#KQ|# Learnings — wireguard-migration
2#KM|
3#RW|## [2026-03-05] 代理类型从 SOCKS5 迁移到 WireGuard
4#RW|
5#ZR|### 项目关键约束
6#TP|- EasyTier VPN Portal 参数格式：`--vpn-portal wg://0.0.0.0:11013/10.14.14.0/24`
7#KW|- 三套客户端使用不同 IP：stash=10.14.14.1, flclash=10.14.14.2, standalone=10.14.14.3
8#BZ|- 代理名称：`Proxy-EasyTier`，代理组：`🦊 EasyTier内网`
9#MW|- 虚拟网段 10.126.126.0/24 保持不变（只是访问目标，不是 WireGuard 子网）
10#KY|- WireGuard 子网：10.14.14.0/24（VPN Portal 内置）
11#XV|- 占位符：YOUR_VPS_IP / YOUR_PRIVATE_KEY / YOUR_PUBLIC_KEY（禁止写入实际密钥）
12#PP|- fetch_servers.py 不得修改
13#BQ|
14#ZQ|### 现有文件状态（修改前）
15#MW|- docker-compose.yml: 包含 `--socks5 15555` 和 `easytier-nginx` 服务（第61-74行）
16#ZM|- stash/easytier.stoverride: type: socks5, port: 15555
17#TV|- flclash/easytier-override.js: type: "socks5", port: 15555
18#KM|- standalone/easytier-standalone.yaml: type: socks5, port: 15555
19#TV|- docker/nginx.conf: 需要删除
20#YR|- docs/socks5-http-latency.md: 需要删除
21#YR|
22#YR|## WireGuard 迁移 learnings
23#YR|### 1. JS 脚本重写
24#YR|- 成功将 `flclash/easytier-override.js` 从 SOCKS5 格式迁移到 WireGuard 格式。
25#YR|- 关键字段更新：`type: "wireguard"`, `server: "YOUR_VPS_IP"`, `port: 11013`, `ip: "10.14.14.2"`, 添加了 `private-key`, `public-key`, `mtu: 1380`, `persistent-keepalive: 25`, `udp: true`。
26#YR|- 语法验证通过，grep 验证了 `wireguard` 类型存在且 `socks5` 不存在。
27#YR|- IP 地址 `10.14.14.2` 正确使用。
28#YR|
29#YR|### 2. standalone/easytier-standalone.yaml 重写
30#YR|- **`standalone/easytier-standalone.yaml` 已重写，代理类型从 `socks5` 改为 `wireguard`。**
31#YR|- `type: wireguard` 已验证。
32#YR|- IP 地址 `10.14.14.3` 已正确配置。
33#YR|- 包含 `private-key` 和 `public-key` 占位符字段。
34#YR|- `mtu: 1380`, `persistent-keepalive: 25`, `udp: true` 已包含。
35#YR|- 代理组结构（`🦊 EasyTier内网`, `🚀 节点选择`, `🎯 直连`）保持不变。
36#YR|- 规则（IP-CIDR + GEOIP + MATCH）保持不变。
37#YR|- YAML 语法正确。
38#YR|
39#YR|**Commit Message**: `refactor(clients): 三套客户端配置从 SOCKS5 迁移到 WireGuard`
## WireGuard Migration (stash/easytier.stoverride)

- Migrated stash/easytier.stoverride from SOCKS5 to WireGuard.
- Verified type, IP, port, and placeholder keys.
- Confirmed proxy name, group, and rule CIDR remain unchanged.
- YAML syntax validated.
- Old SOCKS5 configuration removed.

