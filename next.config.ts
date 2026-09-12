import type { NextConfig } from "next";
import { execSync } from "child_process";

let commitSha = "unknown";
try {
  commitSha = execSync('git rev-parse --short HEAD').toString().trim();
} catch (e) {
  // Ignore
}

const nextConfig: NextConfig = {
  /* config options here */
  reactStrictMode: false,
  output: 'export',
  images: {
    unoptimized: true,
  },
  reactCompiler: true,
  allowedDevOrigins: ["*.ngrok-free.app"],
  env: {
    NEXT_PUBLIC_COMMIT_SHA: commitSha,
  }
};

export default nextConfig;
