/** @type {import('next').NextConfig} */
const API_BASE = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BASE}/api/:path*`,
      },
    ];
  },
  // LLM calls (retro, conditions) can take 30–90s; the default proxy timeout
  // in Next.js is ~30s which causes ECONNRESET / socket hang up.
  // Bump to 180s to accommodate slow reasoning models.
  experimental: {
    proxyTimeout: 180_000,
  },
};

export default nextConfig;
