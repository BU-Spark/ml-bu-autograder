/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['api.autograder.bu.edu'],
    formats: ['image/avif', 'image/webp'],
  },
  // Redirect from root to dashboard
  async redirects() {
    return [
      {
        source: '/',
        destination: '/courses',
        permanent: true,
      },
    ];
  },
  // Environment variables available to the browser
  publicRuntimeConfig: {
    // Will be available on both server and client
    appVersion: process.env.npm_package_version,
  },
  // Add trailing slashes to URLs
  trailingSlash: true,
};

module.exports = nextConfig;