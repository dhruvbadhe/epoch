import type { NextConfig } from "next";
const config: NextConfig = {
  devIndicators: false,
  poweredByHeader: false,
  // OneDrive can hold directory handles; update outputs without removing folders.
  cleanDistDir: false,
  // Keep production and development outputs separate on Windows/OneDrive.
  distDir: process.env.NODE_ENV === "production" ? ".next-production" : ".next",
};
export default config;
