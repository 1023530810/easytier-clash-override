function main(config) {

  // ========== 1. 新增 EasyTier WireGuard 代理（指向 VPS） ==========
  // 获取客户端配置：docker exec -it easytier easytier-cli vpn-portal
  // 此配置默认使用 IP 10.14.14.2（Android 设备）
  // 每台设备需使用不同 IP，如 10.14.14.1 / .2 / .3
  const easyTierProxy = {
    name: "Proxy-EasyTier",
    type: "wireguard",
    server: "YOUR_VPS_IP",      // ← VPS 公网 IP
    port: 11013,                  // ← WireGuard UDP 端口
    ip: "10.14.14.2",            // ← 此设备在 VPN Portal 中的 IP（Android）
    "private-key": "YOUR_PRIVATE_KEY",
    "public-key": "YOUR_PUBLIC_KEY",
    udp: true,
    mtu: 1380,
    "persistent-keepalive": 25
  };

  if (!config.proxies) config.proxies = [];
  config.proxies.push(easyTierProxy);

  // ========== 2. 新增代理组 ==========
  const easyTierGroup = {
    name: "🦊 EasyTier内网",
    type: "select",
    proxies: ["Proxy-EasyTier"]
  };

  if (!config["proxy-groups"]) config["proxy-groups"] = [];
  config["proxy-groups"].push(easyTierGroup);

  // ========== 3. 前置规则（只拦截 EasyTier 虚拟网段） ==========
  const newRules = [
    "IP-CIDR,10.126.126.0/24,🦊 EasyTier内网,no-resolve"
  ];

  if (!config.rules) config.rules = [];
  config.rules.unshift(...newRules);

  return config;
}
