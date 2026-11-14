import {fileURLToPath} from 'node:url';

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{source: '/api/:path*', destination: `${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/:path*`}];
  },
  turbopack: {root: fileURLToPath(new URL('.', import.meta.url))},
};
export default nextConfig;
