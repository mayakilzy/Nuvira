/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone", // produces a minimal self-contained server for Docker
  turbopack: { root: __dirname },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8995",
  },
};
module.exports = nextConfig;
