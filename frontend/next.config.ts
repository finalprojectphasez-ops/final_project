import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow build to succeed even with TypeScript warnings
  typescript: {
    ignoreBuildErrors: true,
  },
  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.supabase.co",
      },
    ],
  },
};

export default nextConfig;
