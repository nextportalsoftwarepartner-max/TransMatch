import type { NextConfig } from "next";

// The browser only ever talks to this app; /api/* is forwarded to the NestJS
// API, so the session cookie stays same-origin.
const API_URL = process.env.API_URL ?? "http://localhost:3201";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
