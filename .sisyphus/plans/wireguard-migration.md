# WireGuard 迁移：SOCKS5 → EasyTier 内置 VPN Portal

## TL;DR

> **Quick Summary**: 将项目从 SOCKS5 代理方案迁移到 EasyTier 内置的 WireGuard VPN Portal，消除 SOCKS5 逐请求握手延迟，同时移除不再需要的 nginx 反向代理。
> 
> **Deliverables**:
> - 修改 docker-compose.yml（删 SOCKS5 + nginx，加 VPN Portal 参数）
> - 更新三套客户端配置（stash/flclash/standalone）为 WireGuard 代理类型
> - 删除旧文件（nginx.conf、socks5-http-latency.md）
> - 完整重写 README.md 和 AGENTS.md
> 
> **Estimated Effort**: Short
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: T1 (docker-compose) → T6 (README) → F1-F4

---

## Context

### Original Request

用户要求将整个项目从 SOCKS5 代理方案重构为 WireGuard L3 隧道方案，解决 SOCKS5 逐请求握手导致 Web 页面卡死的根本问题。

### Interview Summary

**Key Discussions**:
- SOCKS5 每请求 ~520ms，30 请求叠加后页面加载 2.6s+，卡到无法使用
- nginx 反向代理虽然解决延迟，但需要逐端口手动配置，运维麻烦
- WireGuard 作为 L3 隧道，TCP 连接在隧道中透明传输，HTTP Keep-Alive 天然生效
- Mihomo (FlClash) 和 Stash 均原生支持 WireGuard 作为代理节点类型
- 用户选择 Docker 部署、提供添加客户端脚本、删除所有旧文件

**Research Findings**:
- Mihomo WireGuard 代理格式：https://wiki.metacubex.one/en/config/proxies/wg/
- Stash 确认支持 WireGuard 作为 L4 代理（stash.wiki）
- Stash 性能注意事项：WireGuard 用户空间实现吞吐量略低于 L4 代理，但延迟改善远大于吞吐量损失

### Metis Review

**🚨 重大发现：EasyTier 内置 WireGuard VPN Portal**

EasyTier 自身已内置 WireGuard 服务器功能（`--vpn-portal` 参数），只需在 docker-compose.yml 中加一行参数即可。密钥从 network_name + network_secret 确定性派生，无需手动 `wg genkey`。

**这意味着原计划中以下部分全部不需要：**
- ❌ 单独的 WireGuard Docker 容器 (linuxserver/wireguard)
- ❌ IP 转发 (sysctl + iptables FORWARD)
- ❌ `scripts/setup-wireguard.sh`（只需加一行 docker-compose 参数）
- ❌ `scripts/add-client.sh`（密钥自动派生，只需选不同 IP）
- ❌ WireGuard 子网 10.200.0.0/24（改用 VPN Portal 内置子网 10.14.14.0/24）

**Identified Gaps (addressed)**:
- UDP 防火墙：README 中说明需要开放 UDP 11013
- 多客户端 IP 分配：三套配置预分配不同 IP (.1/.2/.3)
- Stash 性能 trade-off：README 中说明
- fetch_servers.py 兼容性：已验证不受影响（只操作 `-p` 行）

---

## Work Objectives

### Core Objective

将手机到 VPS 的通道从 L5 代理（SOCKS5）替换为 L3 隧道（WireGuard VPN Portal），消除逐请求握手延迟，同时删除不再需要的 nginx 反向代理。

### Concrete Deliverables

- `docker/docker-compose.yml`：删除 `--socks5 15555` 和 nginx 服务，新增 `--vpn-portal`
- `stash/easytier.stoverride`：WireGuard 代理格式
- `flclash/easytier-override.js`：WireGuard 代理格式
- `standalone/easytier-standalone.yaml`：WireGuard 代理格式
- `README.md`：完整重写
- `AGENTS.md`：更新项目知识库
- 删除 `docker/nginx.conf` 和 `docs/socks5-http-latency.md`

### Definition of Done

- [ ] `docker-compose.yml` 包含 `--vpn-portal` 参数，不包含 `--socks5` 和 `easytier-nginx`
- [ ] 三套客户端配置均为 `type: wireguard`，使用正确的 Mihomo WireGuard 格式
- [ ] `nginx.conf` 和 `socks5-http-latency.md` 已删除
- [ ] README 完整反映新架构
- [ ] `fetch_servers.py` 未被修改

### Must Have

- WireGuard 代理格式严格遵循 Mihomo 官方文档（https://wiki.metacubex.one/en/config/proxies/wg/）
- 三套客户端配置使用不同的默认 IP（stash: 10.14.14.1, flclash: 10.14.14.2, standalone: 10.14.14.3）
- 代理名称保持 `Proxy-EasyTier`，代理组名称保持 `🦊 EasyTier内网`
- README 包含"为什么选择 WireGuard"章节（从 socks5-http-latency.md 提炼核心结论）
- README 包含获取 WireGuard 客户端配置的步骤（`easytier-cli vpn-portal`）
- README 包含防火墙配置说明（UDP 11013 替代 TCP 15555）

### Must NOT Have (Guardrails)

- **不得**在 repo 中写入实际的 private-key/public-key 值，使用 `YOUR_PRIVATE_KEY`/`YOUR_PUBLIC_KEY` 占位符
- **不得**修改 `scripts/fetch_servers.py`（该脚本只操作 `-p` 行，与 `--vpn-portal` 无关）
- **不得**修改 `-p` 中继服务器行的格式（`fetch_servers.py` 依赖该格式）
- **不得**修改 `easytier-web` 服务配置
- **不得**修改 EasyTier 虚拟网段 10.126.126.0/24
- **不得**添加额外的 Docker 容器（WireGuard 由 EasyTier 内置处理）
- **不得**添加 iptables/sysctl 配置（EasyTier 内部路由不需要）
- **不得**拦截局域网网段（192.168.0.0/16 等）
- **不得**引入项目外的依赖（保持零依赖）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision

- **Infrastructure exists**: NO（纯配置/脚本项目，无测试框架）
- **Automated tests**: None
- **Framework**: none

### QA Policy

Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Config files**: Use Bash (grep/python yaml parse) — Validate syntax, verify key fields
- **Docker**: Use Bash (docker compose config) — Validate compose syntax
- **Deletions**: Use Bash (test -f) — Verify files removed
- **Documentation**: Use Bash (grep) — Verify key sections exist

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — all independent, MAX PARALLEL):
├── Task 1: docker-compose.yml 修改 [quick]
├── Task 2: stash/easytier.stoverride 重写 [quick]
├── Task 3: flclash/easytier-override.js 重写 [quick]
├── Task 4: standalone/easytier-standalone.yaml 重写 [quick]
├── Task 5: 删除旧文件 (nginx.conf + socks5-http-latency.md) [quick]

Wave 2 (After Wave 1 — documentation, need final file state):
├── Task 6: README.md 完整重写 (depends: 1-5) [writing]
├── Task 7: AGENTS.md 更新 (depends: 1-5) [writing]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 6 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks    | Wave |
|------|-----------|-----------|------|
| 1    | —         | 6, 7      | 1    |
| 2    | —         | 6, 7      | 1    |
| 3    | —         | 6, 7      | 1    |
| 4    | —         | 6, 7      | 1    |
| 5    | —         | 6, 7      | 1    |
| 6    | 1-5       | F1-F4     | 2    |
| 7    | 1-5       | F1-F4     | 2    |

### Agent Dispatch Summary

- **Wave 1**: **5 tasks** — T1-T5 → `quick`
- **Wave 2**: **2 tasks** — T6-T7 → `writing`
- **FINAL**: **4 tasks** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [ ] 1. docker-compose.yml 修改：删除 SOCKS5 和 nginx，新增 VPN Portal

  **What to do**:
  - 在 `easytier` 服务的 command 中，删除 `--socks5 15555` 行
  - 在 command 中新增 `--vpn-portal wg://0.0.0.0:11013/10.14.14.0/24` 行（放在 `--hostname` 之前）
  - 删除整个 `easytier-nginx` 服务块（第 61-74 行，从 `# ========== nginx` 注释到最后）
  - 保留 `easytier` 和 `easytier-web` 服务完全不变（除了上述 command 修改）
  - 保留所有 `-p` 中继服务器行的格式不变（fetch_servers.py 依赖该格式）

  **Must NOT do**:
  - 不得修改 `easytier-web` 服务
  - 不得改变 `-p` 行的格式（正则 `^\s+-p\s+` 需保持匹配）
  - 不得修改 `cap_add`、`devices`、`volumes` 等其他配置

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件修改，删几行加一行，改动量极小
  - **Skills**: []
    - 无需额外技能

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `docker/docker-compose.yml:23-44` — 当前 easytier 服务的 command 块，需要修改此处
  - `docker/docker-compose.yml:61-74` — nginx 服务块，需要整体删除

  **API/Type References**:
  - EasyTier VPN Portal 参数格式：`--vpn-portal wg://0.0.0.0:11013/10.14.14.0/24`
  - 官方文档：https://easytier.cn/guide/network/vpn-portal.html
  - DeepWiki 深度分析：https://deepwiki.com/EasyTier/EasyTier/6.5-vpn-portal-and-wireguard-gateway

  **WHY Each Reference Matters**:
  - docker-compose.yml:23-44 — 定位要修改的 command 块，理解现有参数结构
  - docker-compose.yml:61-74 — 定位要删除的 nginx 服务，确保删除范围正确
  - EasyTier VPN Portal 文档 — 确认参数格式和默认端口

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: docker-compose.yml 包含 vpn-portal 参数
    Tool: Bash (grep)
    Preconditions: Task 完成后的 docker/docker-compose.yml
    Steps:
      1. grep 'vpn-portal' docker/docker-compose.yml
      2. 确认输出包含 'wg://0.0.0.0:11013/10.14.14.0/24'
    Expected Result: 输出匹配行包含完整的 vpn-portal 参数
    Failure Indicators: grep 无匹配（退出码 1）
    Evidence: .sisyphus/evidence/task-1-vpn-portal-present.txt

  Scenario: docker-compose.yml 不再包含 socks5
    Tool: Bash (grep)
    Preconditions: Task 完成后的 docker/docker-compose.yml
    Steps:
      1. grep -c 'socks5' docker/docker-compose.yml
    Expected Result: 输出 0
    Failure Indicators: 输出大于 0
    Evidence: .sisyphus/evidence/task-1-no-socks5.txt

  Scenario: docker-compose.yml 不再包含 nginx 服务
    Tool: Bash (grep)
    Preconditions: Task 完成后的 docker/docker-compose.yml
    Steps:
      1. grep -c 'easytier-nginx' docker/docker-compose.yml
    Expected Result: 输出 0
    Failure Indicators: 输出大于 0
    Evidence: .sisyphus/evidence/task-1-no-nginx.txt

  Scenario: docker-compose.yml YAML 语法正确
    Tool: Bash (python3)
    Preconditions: 系统有 python3 + pyyaml 或 docker compose config
    Steps:
      1. cd docker && docker compose config --quiet 2>&1 || python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"
    Expected Result: 无错误输出
    Failure Indicators: YAML 解析错误
    Evidence: .sisyphus/evidence/task-1-yaml-valid.txt
  ```

  **Commit**: YES
  - Message: `refactor(docker): 替换 SOCKS5 为 WireGuard VPN Portal，移除 nginx 服务`
  - Files: `docker/docker-compose.yml`

---

- [ ] 2. stash/easytier.stoverride 重写为 WireGuard 代理格式

  **What to do**:
  - 将 `type: socks5` 改为 `type: wireguard`
  - 删除 `port: 15555` 和 `udp: true`（SOCKS5 特有字段）
  - 新增 WireGuard 必须字段：`port: 11013`、`ip: 10.14.14.1`、`private-key: YOUR_PRIVATE_KEY`、`public-key: YOUR_PUBLIC_KEY`、`udp: true`、`mtu: 1380`、`persistent-keepalive: 25`
  - 保持 `name: Proxy-EasyTier` 和 `server: YOUR_VPS_IP` 不变
  - 保持代理组 `🦊 EasyTier内网` 和规则 `IP-CIDR,10.126.126.0/24` 不变
  - 更新 `name` 和 `desc` 描述文本（提到 WireGuard 而非 SOCKS5）
  - IP 注释说明：「每台设备需使用不同 IP，如 10.14.14.1 / .2 / .3」
  - 添加注释说明如何获取 private-key 和 public-key（`docker exec -it easytier easytier-cli vpn-portal`）

  **Must NOT do**:
  - 不得写入实际密钥值
  - 不得修改规则网段 10.126.126.0/24
  - 不得修改代理组名称

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件覆写，约 25 行 YAML
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `stash/easytier.stoverride:1-21` — 当前完整文件，需要在此基础上修改代理类型

  **API/Type References**:
  - Mihomo WireGuard 代理格式（简化写法）：https://wiki.metacubex.one/en/config/proxies/wg/
  - Stash WireGuard 支持确认：https://stash.wiki/en/proxy-protocols/proxy-types（底部 WireGuard 章节）

  **WHY Each Reference Matters**:
  - 当前 stoverride 文件 — 理解现有结构，保持代理组和规则不变
  - Mihomo 文档 — WireGuard 字段格式的权威参考（Stash 兼容此格式）

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: stoverride 包含 wireguard 类型
    Tool: Bash (grep)
    Steps:
      1. grep -c 'type: wireguard' stash/easytier.stoverride
    Expected Result: 输出 1
    Evidence: .sisyphus/evidence/task-2-wireguard-type.txt

  Scenario: stoverride YAML 语法正确
    Tool: Bash (python3)
    Steps:
      1. python3 -c "import yaml; yaml.safe_load(open('stash/easytier.stoverride'))"
    Expected Result: 无错误退出
    Evidence: .sisyphus/evidence/task-2-yaml-valid.txt

  Scenario: stoverride 不包含 socks5
    Tool: Bash (grep)
    Steps:
      1. grep -c 'socks5' stash/easytier.stoverride
    Expected Result: 输出 0
    Evidence: .sisyphus/evidence/task-2-no-socks5.txt

  Scenario: stoverride 包含必须的 WireGuard 字段
    Tool: Bash (grep)
    Steps:
      1. grep 'private-key' stash/easytier.stoverride
      2. grep 'public-key' stash/easytier.stoverride
      3. grep 'ip: 10.14.14.1' stash/easytier.stoverride
      4. grep 'port: 11013' stash/easytier.stoverride
    Expected Result: 全部匹配
    Evidence: .sisyphus/evidence/task-2-wg-fields.txt
  ```

  **Commit**: YES (groups with 3, 4)
  - Message: `refactor(clients): 三套客户端配置从 SOCKS5 迁移到 WireGuard`
  - Files: `stash/easytier.stoverride`, `flclash/easytier-override.js`, `standalone/easytier-standalone.yaml`

---

- [ ] 3. flclash/easytier-override.js 重写为 WireGuard 代理格式

  **What to do**:
  - 将 `easyTierProxy` 对象从 socks5 格式改为 wireguard 格式
  - 新的对象字段：`type: "wireguard"`, `server: "YOUR_VPS_IP"`, `port: 11013`, `ip: "10.14.14.2"`, `"private-key": "YOUR_PRIVATE_KEY"`, `"public-key": "YOUR_PUBLIC_KEY"`, `udp: true`, `mtu: 1380`, `"persistent-keepalive": 25`
  - 注意 JS 对象中带连字符的 key 需要用引号包裹（`"private-key"`）
  - 保持 `name: "Proxy-EasyTier"` 不变
  - 保持代理组名称和规则不变
  - 更新注释文本（提到 WireGuard 而非 SOCKS5）
  - 注释说明 IP 分配：此配置默认 10.14.14.2（Android 设备）
  - 添加注释说明如何获取密钥

  **Must NOT do**:
  - 不得写入实际密钥值
  - 不得修改 main(config) 函数签名
  - 不得修改规则和代理组逻辑

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件覆写，约 35 行 JS
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `flclash/easytier-override.js:1-34` — 当前完整文件，需要修改 easyTierProxy 对象

  **API/Type References**:
  - Mihomo WireGuard 字段名：https://wiki.metacubex.one/en/config/proxies/wg/
  - FlClash 覆写脚本格式：https://github.com/chen08209/FlClash/issues/1510

  **WHY Each Reference Matters**:
  - 当前 JS 文件 — 保持函数结构和逻辑不变，只替换代理对象内容
  - Mihomo 文档 — 确认字段名和类型（JS 对象中字段名需与 YAML key 一致）

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: JS 脚本语法正确
    Tool: Bash (node)
    Steps:
      1. node -e "const fs=require('fs'); eval(fs.readFileSync('flclash/easytier-override.js','utf8')); console.log(typeof main)"
    Expected Result: 输出 "function"
    Evidence: .sisyphus/evidence/task-3-js-valid.txt

  Scenario: JS 脚本包含 wireguard 类型
    Tool: Bash (grep)
    Steps:
      1. grep -c '"wireguard"' flclash/easytier-override.js
    Expected Result: 输出 1
    Evidence: .sisyphus/evidence/task-3-wireguard-type.txt

  Scenario: JS 脚本不包含 socks5
    Tool: Bash (grep)
    Steps:
      1. grep -c 'socks5' flclash/easytier-override.js
    Expected Result: 输出 0
    Evidence: .sisyphus/evidence/task-3-no-socks5.txt

  Scenario: JS 脚本使用正确的 IP
    Tool: Bash (grep)
    Steps:
      1. grep '10.14.14.2' flclash/easytier-override.js
    Expected Result: 匹配到 IP 分配
    Evidence: .sisyphus/evidence/task-3-ip-correct.txt
  ```

  **Commit**: YES (groups with 2, 4)
  - Message: `refactor(clients): 三套客户端配置从 SOCKS5 迁移到 WireGuard`
  - Files: `stash/easytier.stoverride`, `flclash/easytier-override.js`, `standalone/easytier-standalone.yaml`

---

- [ ] 4. standalone/easytier-standalone.yaml 重写为 WireGuard 代理格式

  **What to do**:
  - 将 `type: socks5` 改为 `type: wireguard`
  - 删除 `port: 15555` 和 `udp: true`（SOCKS5 特有字段）
  - 新增 WireGuard 字段：`port: 11013`、`ip: 10.14.14.3`、`private-key: YOUR_PRIVATE_KEY`、`public-key: YOUR_PUBLIC_KEY`、`udp: true`、`mtu: 1380`、`persistent-keepalive: 25`
  - 保持代理组和规则不变
  - 更新注释文本
  - IP 注释说明：此配置默认 10.14.14.3（第三台设备）
  - 添加注释说明如何获取密钥

  **Must NOT do**:
  - 不得写入实际密钥值
  - 不得修改代理组结构和规则

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件覆写，约 40 行 YAML
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `standalone/easytier-standalone.yaml:1-37` — 当前完整文件

  **API/Type References**:
  - Mihomo WireGuard 格式：https://wiki.metacubex.one/en/config/proxies/wg/

  **WHY Each Reference Matters**:
  - 当前 YAML 文件 — 理解现有代理组和规则结构，只替换代理定义

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: standalone 包含 wireguard 类型
    Tool: Bash (grep)
    Steps:
      1. grep -c 'type: wireguard' standalone/easytier-standalone.yaml
    Expected Result: 输出 1
    Evidence: .sisyphus/evidence/task-4-wireguard-type.txt

  Scenario: standalone YAML 语法正确
    Tool: Bash (python3)
    Steps:
      1. python3 -c "import yaml; yaml.safe_load(open('standalone/easytier-standalone.yaml'))"
    Expected Result: 无错误退出
    Evidence: .sisyphus/evidence/task-4-yaml-valid.txt

  Scenario: standalone 使用正确的 IP
    Tool: Bash (grep)
    Steps:
      1. grep '10.14.14.3' standalone/easytier-standalone.yaml
    Expected Result: 匹配到 IP 分配
    Evidence: .sisyphus/evidence/task-4-ip-correct.txt
  ```

  **Commit**: YES (groups with 2, 3)
  - Message: `refactor(clients): 三套客户端配置从 SOCKS5 迁移到 WireGuard`
  - Files: `stash/easytier.stoverride`, `flclash/easytier-override.js`, `standalone/easytier-standalone.yaml`

---

- [ ] 5. 删除旧文件：nginx.conf 和 socks5-http-latency.md

  **What to do**:
  - 删除 `docker/nginx.conf`
  - 删除 `docs/socks5-http-latency.md`
  - 如果 `docs/` 目录变为空，删除该目录

  **Must NOT do**:
  - 不得删除 docs 以外的任何文件
  - 不得删除 docker/ 目录下的其他文件

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯删除操作，两条 rm 命令
  - **Skills**: [`git-master`]
    - `git-master`: 需要 git rm 正确删除并暂存

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `docker/nginx.conf` — 要删除的文件
  - `docs/socks5-http-latency.md` — 要删除的文件

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: nginx.conf 已删除
    Tool: Bash (test)
    Steps:
      1. test ! -f docker/nginx.conf && echo "OK"
    Expected Result: 输出 OK
    Evidence: .sisyphus/evidence/task-5-nginx-deleted.txt

  Scenario: socks5-http-latency.md 已删除
    Tool: Bash (test)
    Steps:
      1. test ! -f docs/socks5-http-latency.md && echo "OK"
    Expected Result: 输出 OK
    Evidence: .sisyphus/evidence/task-5-doc-deleted.txt
  ```

  **Commit**: YES
  - Message: `refactor: 删除 nginx 和 SOCKS5 延迟文档（已被 WireGuard 方案替代）`
  - Files: `docker/nginx.conf`, `docs/socks5-http-latency.md`

---

- [ ] 6. README.md 完整重写

  **What to do**:
  - 完整重写 README.md，替换所有 SOCKS5/nginx 相关内容为 WireGuard VPN Portal
  - 必须包含以下章节：
    1. **项目简介**：EasyTier + Clash 共存方案（WireGuard 版）
    2. **问题背景**：手机只能开一个 VPN → 需要中转
    3. **为什么选择 WireGuard**：从 socks5-http-latency.md 提炼核心结论（SOCKS5 逐请求握手延迟 vs WireGuard L3 隧道），用简短对比表说明
    4. **解决方案架构图**：手机(Clash WireGuard节点) → VPS(EasyTier VPN Portal) → 虚拟网络
    5. **VPS 部署**：Docker 部署步骤，重点说明 `--vpn-portal` 参数
    6. **获取客户端配置**：`docker exec -it easytier easytier-cli vpn-portal` → 翻译为 Clash YAML 的步骤
    7. **客户端配置**：Stash / FlClash / Standalone 的使用说明
    8. **防火墙配置**：UDP 11013（替代原来的 TCP 15555）
    9. **安全说明**：WireGuard 加密 + 密钥认证（比 SOCKS5 无认证更安全）
    10. **注意事项**：移动端 WireGuard 吞吐量 trade-off、测速失败是正常的、ICMP 不可用
    11. **Web Console**：保持不变，从原 README 复制
    12. **服务器列表抓取工具**：保持不变，从原 README 复制
    13. **常见问题**：更新 Q&A 反映新方案
    14. **参考资料**：更新链接（添加 EasyTier VPN Portal 文档、Mihomo WireGuard 文档）
  - 保持中文风格
  - 架构图用 ASCII art（与现有风格一致）

  **Must NOT do**:
  - 不得保留任何 SOCKS5 或 nginx 的操作指南（仅可在「为什么选择 WireGuard」章节简述旧方案问题）
  - 不得写入实际密钥值
  - 不得修改项目实际的技术方案（必须与 docker-compose.yml 和客户端配置一致）
  - 不得使用 emoji（除了已有的 🦊 代理组名称）

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 大篇幅技术文档重写，需要清晰的结构和准确的技术细节
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 1, 2, 3, 4, 5（需要知道最终文件状态）

  **References**:

  **Pattern References**:
  - `README.md:1-全部` — 当前完整 README，理解现有结构和风格，作为重写基础
  - `docker/docker-compose.yml`（修改后）— 确认 vpn-portal 参数和服务结构
  - `stash/easytier.stoverride`（修改后）— 确认客户端配置格式
  - `flclash/easytier-override.js`（修改后）— 确认客户端配置格式
  - `standalone/easytier-standalone.yaml`（修改后）— 确认客户端配置格式

  **External References**:
  - EasyTier VPN Portal 文档：https://easytier.cn/guide/network/vpn-portal.html
  - EasyTier GitHub：https://github.com/EasyTier/EasyTier
  - Mihomo WireGuard 文档：https://wiki.metacubex.one/en/config/proxies/wg/
  - Stash WireGuard 支持：https://stash.wiki/en/proxy-protocols/proxy-types
  - Stash 覆写文档：https://stash.wiki/configuration/override
  - FlClash 覆写脚本：https://github.com/chen08209/FlClash/issues/1510

  **WHY Each Reference Matters**:
  - 现有 README — 复用 Web Console 和服务器列表工具的章节，保持项目风格一致性
  - 修改后的配置文件 — README 中的代码示例必须与实际文件一致
  - 外部文档 — 确保参考资料链接准确有效

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README 包含 WireGuard 关键章节
    Tool: Bash (grep)
    Steps:
      1. grep -c 'WireGuard' README.md
      2. grep -c 'vpn-portal' README.md
      3. grep -c 'easytier-cli vpn-portal' README.md
      4. grep -c '11013' README.md
    Expected Result: 所有 grep 输出 >= 1
    Evidence: .sisyphus/evidence/task-6-readme-sections.txt

  Scenario: README 不包含 SOCKS5 操作指南
    Tool: Bash (grep)
    Steps:
      1. grep -c 'port: 15555' README.md
      2. grep -c 'nginx.conf' README.md
    Expected Result: 两个 grep 输出均为 0
    Failure Indicators: 残留 SOCKS5/nginx 操作指南
    Evidence: .sisyphus/evidence/task-6-no-socks5-guide.txt

  Scenario: README 包含防火墙说明
    Tool: Bash (grep)
    Steps:
      1. grep -c 'UDP.*11013\|11013.*UDP\|udp.*11013\|11013.*udp' README.md
    Expected Result: >= 1
    Evidence: .sisyphus/evidence/task-6-firewall.txt
  ```

  **Commit**: YES
  - Message: `docs(readme): 完整重写 README，反映 WireGuard VPN Portal 新架构`
  - Files: `README.md`

---

- [ ] 7. AGENTS.md 更新项目知识库

  **What to do**:
  - 更新 OVERVIEW：提到 WireGuard VPN Portal 替代 SOCKS5
  - 更新 STRUCTURE：移除 nginx.conf 和 docs/，反映新的文件结构
  - 更新 WHERE TO LOOK 表格：
    - 「部署 VPS 节点」→ 提到 `--vpn-portal` 参数
    - 删除「添加 HTTP 服务直通」行（nginx 已删除）
    - 新增「获取 WireGuard 客户端配置」→ `easytier-cli vpn-portal`
  - 更新 CONVENTIONS：如有 SOCKS5 相关约定需替换
  - 更新 ANTI-PATTERNS：
    - 删除「不要暴露 SOCKS5 端口」
    - 新增「确保 VPS 防火墙开放 UDP 11013」
    - 保留「SOCKS5 不能 ping」→ 改为「WireGuard 隧道通过 Clash 代理时不支持 ICMP」
  - 更新 COMMANDS：
    - 删除 SOCKS5 相关验证命令
    - 新增 `docker exec -it easytier easytier-cli vpn-portal`
  - 更新 NOTES：移除 nginx 相关说明

  **Must NOT do**:
  - 不得修改 AGENTS.md 的格式结构（保持 ## 层级一致）
  - 不得删除 fetch_servers.py 相关说明

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 结构化知识库更新，需要准确反映新架构
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (与 Task 6 并行)
  - **Parallel Group**: Wave 2 (with Task 6)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 1, 2, 3, 4, 5

  **References**:

  **Pattern References**:
  - `AGENTS.md:1-全部` — 当前完整文件，理解现有格式和结构

  **WHY Each Reference Matters**:
  - 当前 AGENTS.md — 保持格式结构不变，只替换内容

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: AGENTS.md 包含 WireGuard/VPN Portal 内容
    Tool: Bash (grep)
    Steps:
      1. grep -c 'vpn-portal' AGENTS.md
      2. grep -c 'WireGuard' AGENTS.md
    Expected Result: 两个 grep 输出均 >= 1
    Evidence: .sisyphus/evidence/task-7-agents-updated.txt

  Scenario: AGENTS.md 不包含 nginx/SOCKS5 操作
    Tool: Bash (grep)
    Steps:
      1. grep -c 'nginx.conf' AGENTS.md
      2. grep -c 'socks5-http-latency' AGENTS.md
    Expected Result: 两个 grep 输出均为 0
    Evidence: .sisyphus/evidence/task-7-no-old-refs.txt
  ```

  **Commit**: YES
  - Message: `docs(agents): 更新项目知识库，反映 WireGuard VPN Portal 架构`
  - Files: `AGENTS.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, grep). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Review all changed files for: YAML 语法正确性（python3 yaml.safe_load）、JS 语法正确性（node eval）、docker-compose 语法（docker compose config）、注释完整性、占位符一致性（YOUR_VPS_IP/YOUR_PRIVATE_KEY/YOUR_PUBLIC_KEY 统一）。检查三套客户端配置的代理名称、规则格式是否一致。
  Output: `YAML [PASS/FAIL] | JS [PASS/FAIL] | Docker [PASS/FAIL] | Consistency [PASS/FAIL] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task consistency: 三套配置的 WireGuard 端口(11013)、public-key 占位符、规则网段(10.126.126.0/24) 是否一致。验证 docker-compose.yml 中 vpn-portal 子网(10.14.14.0/24) 与客户端配置 IP(10.14.14.1/2/3) 一致。Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Consistency [N/N] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Verify `scripts/fetch_servers.py` was NOT modified (`git diff --name-only scripts/fetch_servers.py` 输出为空). Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| 序号 | Commit Message | 文件 |
|------|---------------|------|
| 1 | `refactor(docker): 替换 SOCKS5 为 WireGuard VPN Portal，移除 nginx 服务` | `docker/docker-compose.yml` |
| 2 | `refactor(clients): 三套客户端配置从 SOCKS5 迁移到 WireGuard` | `stash/easytier.stoverride`, `flclash/easytier-override.js`, `standalone/easytier-standalone.yaml` |
| 3 | `refactor: 删除 nginx 和 SOCKS5 延迟文档（已被 WireGuard 方案替代）` | `docker/nginx.conf`, `docs/socks5-http-latency.md` |
| 4 | `docs(readme): 完整重写 README，反映 WireGuard VPN Portal 新架构` | `README.md` |
| 5 | `docs(agents): 更新项目知识库，反映 WireGuard VPN Portal 架构` | `AGENTS.md` |

---

## Success Criteria

### Verification Commands

```bash
# 1. docker-compose 语法验证
cd docker && docker compose config --quiet  # Expected: 无错误输出

# 2. VPN Portal 参数存在
grep 'vpn-portal' docker/docker-compose.yml  # Expected: 包含 wg://0.0.0.0:11013

# 3. SOCKS5 已移除
grep -c 'socks5' docker/docker-compose.yml  # Expected: 0

# 4. nginx 已移除
grep -c 'easytier-nginx' docker/docker-compose.yml  # Expected: 0
test ! -f docker/nginx.conf && echo OK  # Expected: OK

# 5. 旧文档已删除
test ! -f docs/socks5-http-latency.md && echo OK  # Expected: OK

# 6. 三套配置均为 WireGuard
grep -c 'type: wireguard' stash/easytier.stoverride  # Expected: 1
grep -c '"wireguard"' flclash/easytier-override.js  # Expected: 1
grep -c 'type: wireguard' standalone/easytier-standalone.yaml  # Expected: 1

# 7. 三套配置使用不同 IP
grep '10.14.14.1' stash/easytier.stoverride  # Expected: 匹配
grep '10.14.14.2' flclash/easytier-override.js  # Expected: 匹配
grep '10.14.14.3' standalone/easytier-standalone.yaml  # Expected: 匹配

# 8. fetch_servers.py 未被修改
git diff --name-only scripts/fetch_servers.py  # Expected: 无输出
```

### Final Checklist

- [ ] docker-compose.yml 包含 `--vpn-portal wg://0.0.0.0:11013/10.14.14.0/24`
- [ ] docker-compose.yml 不包含 `--socks5` 和 `easytier-nginx`
- [ ] 三套客户端配置均为 `type: wireguard`，端口 11013
- [ ] 三套配置使用不同 IP（.1 / .2 / .3）
- [ ] 所有配置使用占位符（YOUR_VPS_IP / YOUR_PRIVATE_KEY / YOUR_PUBLIC_KEY）
- [ ] nginx.conf 和 socks5-http-latency.md 已删除
- [ ] README 完整反映新架构
- [ ] AGENTS.md 已更新
- [ ] fetch_servers.py 未被修改
- [ ] 所有 YAML 文件语法正确
- [ ] JS 脚本语法正确
