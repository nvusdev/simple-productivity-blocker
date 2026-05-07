/** @type {import('next').NextConfig} */
const isGithubActions = process.env.GITHUB_ACTIONS || false;

const nextConfig = {
  output: 'export',
  basePath: isGithubActions ? '/simple-productivity-blocker' : '',
  assetPrefix: isGithubActions ? '/simple-productivity-blocker/' : '',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
