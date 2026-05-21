/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: '/spb',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
