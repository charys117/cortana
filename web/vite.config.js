import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Build output is served by src/web/server.py (aiohttp).
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: "../src/web/static",
    emptyOutDir: true,
  },
  server: {
    // `npm run dev` proxies API calls to a locally running bot
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/avatars": "http://127.0.0.1:8080",
    },
  },
});
