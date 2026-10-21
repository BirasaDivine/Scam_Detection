/// <reference types="vitest" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // A production build without the API address would point at localhost and never work.
  // Fail the build with a clear message instead of publishing a broken site.
  const env = loadEnv(mode, process.cwd(), "VITE_");
  if (mode === "production" && !env.VITE_API_URL) {
    throw new Error(
      "VITE_API_URL is not set. Set it to your API address, for example https://scamguard-api.onrender.com",
    );
  }

  return {
    plugins: [react()],
    server: { port: 5173, strictPort: true },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test-setup.ts"],
    },
  };
});
