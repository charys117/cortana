import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

// Build output is served by src/web/server.py (aiohttp).
export default defineConfig({
  plugins: [
    vue(),
    // on-demand Element Plus: templates resolve el-* components, scripts
    // resolve ElMessage/ElMessageBox, each with their styles
    AutoImport({ resolvers: [ElementPlusResolver()], dts: false }),
    Components({ resolvers: [ElementPlusResolver()], dts: false }),
  ],
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
