/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // AI inference is bounded at 120s in the backend; allow DB/HTTP overhead.
    // Next's default 30s would return 500 before a slower local model finishes.
    proxyTimeout: 150_000,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_API_URL || 'http://127.0.0.1:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
