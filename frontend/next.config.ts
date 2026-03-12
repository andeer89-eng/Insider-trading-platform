import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  images: {
    remotePatterns: [
      { hostname: "logo.clearbit.com" },
      { hostname: "assets.stickpng.com" },
    ],
  },
};

export default nextConfig;
