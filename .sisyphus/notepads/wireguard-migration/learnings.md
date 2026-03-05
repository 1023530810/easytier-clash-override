# Learnings — wireguard-migration

## [2026-03-05] 初始化

### 项目关键约束
- EasyTier VPN Portal 参数格式：`--vpn-portal wg://0.0.0.0:11013/10.14.14.0/24`
- 三套客户端使用不同 IP：stash=10.14.14.1, flclash=10.14.14.2, standalone=10.14.14.3
- 代理名称：`Proxy-EasyTier`，代理组：`🦊 EasyTier内网`
- 虚拟网段 10.126.126.0/24 保持不变（只是访问目标，不是 WireGuard 子网）
- WireGuard 子网：10.14.14.0/24（VPN Portal 内置）
- 占位符：YOUR_VPS_IP / YOUR_PRIVATE_KEY / YOUR_PUBLIC_KEY（禁止写入实际密钥）
- fetch_servers.py 不得修改

### 现有文件状态（修改前）
- docker-compose.yml: 包含 `--socks5 15555` 和 `easytier-nginx` 服务（第61-74行）
- stash/easytier.stoverride: type: socks5, port: 15555
- flclash/easytier-override.js: type: "socks5", port: 15555
- standalone/easytier-standalone.yaml: type: socks5, port: 15555
- docker/nginx.conf: 需要删除
- docs/socks5-http-latency.md: 需要删除
