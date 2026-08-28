import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: false,
  // In production (unified Cloud Run deploy): proxy /api/* to the FastAPI backend on :8000
  // In dev: the API client uses NEXT_PUBLIC_API_BASE_URL (the Cloud Run backend URL directly)
  async rewrites() {
    if (process.env.NODE_ENV === "production") {
      return [
        {
          source: "/api/:path*",
          destination: "http://localhost:8000/api/:path*",
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
