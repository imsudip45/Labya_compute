/** @type {import('next').NextConfig} */
const nextConfig = {
  // Plain static files: the API serves them (backend/app/main.py), so there's no Node server.
  output: "export",
  trailingSlash: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
