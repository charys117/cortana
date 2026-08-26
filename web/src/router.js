import { createRouter, createWebHistory } from "vue-router";
import ConfigView from "./components/ConfigView.vue";

// History mode: src/web/server.py serves index.html for /archive* so deep
// links survive a refresh.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "config", component: ConfigView },
    {
      path: "/archive/:channelId?",
      name: "archive",
      component: () => import("./components/archive/ArchiveView.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});
