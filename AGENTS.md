# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-04
**Commit:** ef250cd
**Branch:** main

## OVERVIEW

EasyTier + Clash 共存方案。通过 VPS（Docker）运行 EasyTier 并开启 SOCKS5 代理，手机端 Clash 客户端通过覆写规则将虚拟网段流量转发至 VPS，解决手机只能开一个 VPN 的限制。

## STRUCTURE

```
├── docker/                     # VPS Docker 部署（核心）
│   ├── docker-compose.yml      # EasyTier 节点 + Web Console + nginx 编排
│   ├── nginx.conf              # nginx 反向代理配置（HTTP 服务直通）
│   └── .env.example            # ET_NETWORK_NAME / ET_NETWORK_SECRET / ET_WEB_USERNAME
├── stash/                      # iOS Stash 客户端覆写
│   └── easytier.stoverride     # Stash 数组合并格式，追加到订阅前
├── flclash/                    # Android/桌面 FlClash 覆写
│   └── easytier-override.js    # JS 脚本，修改 config 对象注入代理+规则
├── standalone/                 # 无订阅时的完整 Clash 配置
│   └── easytier-standalone.yaml
└── scripts/                    # 工具脚本
    └── fetch_servers.py        # 抓取 Astral 公共服务器列表，支持 --diff/--raw/--update-compose
```

## WHERE TO LOOK

| 任务 | 文件 | 说明 |
|------|------|------|
| 部署 VPS 节点 | `docker/docker-compose.yml` + `docker/.env` | 修改网络凭据和中继服务器 |
| 添加 HTTP 服务直通 | `docker/nginx.conf` | 避免 SOCKS5 延迟叠加，直接反向代理内网 HTTP 服务 |
| 更新中继服务器 | `scripts/fetch_servers.py --update-compose` | 自动替换 compose 中的 `-p` 行 |
| 添加 iOS 客户端支持 | `stash/easytier.stoverride` | YAML 覆写格式 |
| 添加 Android 客户端支持 | `flclash/easytier-override.js` | JS `main(config)` 函数 |
| 无订阅独立使用 | `standalone/easytier-standalone.yaml` | 需手动添加代理节点 |

## CONVENTIONS

- **语言**：README/注释/commit 均使用中文
- **无构建系统**：无 Makefile/CI/linter/formatter，纯配置+脚本项目
- **无测试**：项目无测试文件
- **Python 脚本**：仅用标准库（无第三方依赖），要求 Python 3.9+
- **环境变量前缀**：Docker 环境变量统一用 `ET_` 前缀
- **覆写文件命名**：`easytier-*` 或 `easytier.*` 前缀

## ANTI-PATTERNS（本项目禁止）

- **不要拦截局域网网段**：规则只拦截 `10.126.126.0/24`，禁止拦截 `192.168.0.0/16` 等
- **不要暴露 SOCKS5 端口**：EasyTier SOCKS5 无认证，必须用防火墙限制
- **不要在手机上运行 EasyTier**：iOS 后台挂起 + VPN 隧道干扰组网，方案依赖 VPS 中转
- **SOCKS5 不能 ping**：ICMP 不可用，只能用 TCP 工具（SSH/curl）测试连通性
- **测速会失败**：SOCKS5 只能访问虚拟网络，公网 URL 会超时，这是正常现象

## UNIQUE STYLES

- **三套客户端配置并行维护**：stash（YAML 覆写）/ flclash（JS 脚本）/ standalone（完整 YAML），修改网段/端口时三者需同步
- **docker-compose 中 command 使用 `>` 多行折叠**：`-p` 参数按行排列，`fetch_servers.py --update-compose` 通过正则定位并替换这些行
- **Web Console 可选部署**：`easytier-web` 服务与 `easytier` 节点通过 `depends_on` 关联，通过 `--machine-id` 固定设备标识
- **nginx 反向代理可选部署**：`easytier-nginx` 服务解决 SOCKS5 访问 HTTP 服务卡顿问题，端口在 `nginx.conf` 中按需添加

## COMMANDS

```bash
# VPS 部署
cd docker && cp .env.example .env && nano .env
docker compose up -d
docker compose logs -f

# 容器内验证组网
docker exec -it easytier easytier-cli peer
docker exec -it easytier easytier-cli route

# 抓取公共服务器
python3 scripts/fetch_servers.py              # 完整报告
python3 scripts/fetch_servers.py --diff       # 仅变更
python3 scripts/fetch_servers.py --raw        # 纯 URI 列表
python3 scripts/fetch_servers.py --update-compose  # 自动更新 compose
```

## NOTES

- `docker/data/` 和 `docker/web-data/` 已 gitignore，容器运行时自动生成
- `scripts/.servers_state.json` 已 gitignore，用于 diff 比对的本地状态缓存
- `docker-compose.yml` 中 `network_mode: host` — 容器直接使用宿主网络
- Web Console 注册后需将用户名填入 `.env` 的 `ET_WEB_USERNAME` 并重启容器
- `docker-compose.yml` 中 `--api-host` 的 `YOUR_VPS_IP` 需手动替换
- `docker/nginx.conf` 中的端口和目标 IP 需根据实际 EasyTier 设备调整
