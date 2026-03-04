function main(config) {

  // ========== 1. 新增 EasyTier SOCKS5 代理（指向 VPS） ==========
  const easyTierProxy = {
    name: "Proxy-EasyTier",
    type: "socks5",
    server: "YOUR_VPS_IP",  // ← VPS 公网 IP
    port: 15555,               // ← VPS 上 EasyTier 的 SOCKS5 端口
    udp: true
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
