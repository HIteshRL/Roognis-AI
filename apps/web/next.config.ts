import path from 'path'
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Standalone server for the Docker image; trace from the monorepo root so
  // workspace packages (@roognis/*) are bundled correctly.
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, '../../'),
  transpilePackages: ['@roognis/shared', '@roognis/ui'],
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'img.clerk.com' },
      { protocol: 'https', hostname: 'avatars.githubusercontent.com' },
    ],
  },
}

export default nextConfig
