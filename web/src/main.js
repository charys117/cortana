import { createApp } from "vue";
// components and ElMessage/ElMessageBox are auto-imported on demand (see
// vite.config.js); only the v-loading directive and global css come in here
import { ElLoading } from "element-plus";
import "element-plus/theme-chalk/el-loading.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import "./style.css";
import App from "./App.vue";

const app = createApp(App);
app.directive("loading", ElLoading.directive);
app.mount("#app");
