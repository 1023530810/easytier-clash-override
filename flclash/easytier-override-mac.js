function main(config) {

  // Mac 已原生接入 EasyTier 网络（easytier-core 直接运行）
  // 无需 WireGuard 代理，直接让虚拟网段流量走 DIRECT
  // 不占用 VPN Portal IP，延迟也更低
  // 如需修改网段，调整下方 IP-CIDR 即可

  const newRules = [
    "IP-CIDR,10.126.126.0/24,DIRECT,no-resolve"
  ];

  if (!config.rules) config.rules = [];
  config.rules.unshift(...newRules);

  return config;
}
