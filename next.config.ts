import type { NextConfig } from "next";
import { execSync } from "child_process";

let commitSha = "unknown";
try {
  commitSha = process.env.NEXT_PUBLIC_COMMIT_SHA || process.env.GITHUB_SHA || execSync('git rev-parse --short HEAD').toString().trim();
  if (commitSha.length > 7) {
    commitSha = commitSha.substring(0, 7);
  }
} catch (e) {
  // Ignore
}

const basePath = '/white_monster_api';

const nextConfig: NextConfig = {
  /* config options here */
  basePath,
  reactStrictMode: false,
  output: 'export',
  images: {
    unoptimized: true,
  },
  reactCompiler: true,
  allowedDevOrigins: ["*.ngrok-free.app"],
  env: {
    NEXT_PUBLIC_COMMIT_SHA: commitSha,
    NEXT_PUBLIC_BASE_PATH: basePath,
  }
};

export default nextConfig;
