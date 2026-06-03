import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 允许开发环境的跨域访问（用于局域网访问）
  allowedDevOrigins: ['192.168.119.63'],
};

export default nextConfig;