import { createHash } from "node:crypto"
import { existsSync, readFileSync } from "node:fs"

// Version tag for the agent download links (see lib/downloads.ts).
const hash = createHash("sha256")
for (const f of ["LabhyaComputeAgentSetup.exe", "LabhyaComputeAgent.exe"]) {
  const p = `public/downloads/${f}`
  if (existsSync(p)) hash.update(readFileSync(p))
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Plain static files: the API serves them (backend/app/main.py), so there's no Node server.
  output: "export",
  trailingSlash: true,
  env: {
    NEXT_PUBLIC_AGENT_VERSION: hash.digest("hex").slice(0, 12),
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
