// Mac 已原生接入 EasyTier 网络（easytier-core / easytier-gui 直接运行）
// Mac 无需覆写脚本，也无需 WireGuard 代理
//
// ⚠️ 关键配置：必须在 Clash 的 TUN 设置中排除 EasyTier 网段
//   否则 Clash TUN 会劫持虚拟网段流量，导致连接超时
//
// 操作步骤：
//   1. 打开 Clash Verge / FlClash → 设置 → TUN 模式
//   2. 找到「排除路由地址（route-exclude-address）」
//   3. 添加：10.126.126.0/24
//   4. 保存并重启 TUN
//
// 原理：
//   排除后，10.126.126.0/24 的流量不经过 Clash TUN，
//   直接由 EasyTier 的 TUN 接口处理，延迟最低（~2ms）
//
// 此脚本不做任何修改，仅作为说明文件保留

function main(config) {
  return config;
}
