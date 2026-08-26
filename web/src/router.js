import { createRouter, createWebHistory } from "vue-router";
import ArchiveView from "./components/archive/ArchiveView.vue";
import SettingsView from "./components/SettingsView.vue";

// History mode: src/web/server.py serves index.html for /archive*, /settings
// and /config so deep links survive a refresh. The archive is the default
// view; the config editor lives at /settings.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/archive" },
    { path: "/archive/:channelId?", name: "archive", component: ArchiveView },
    { path: "/settings", name: "settings", component: SettingsView },
    { path: "/config", redirect: "/settings" },
    { path: "/:pathMatch(.*)*", redirect: "/archive" },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition || { top: 0 };
  },
});

// legacy hash deep links from the pre-router UI (#archive/<id>, #settings,
// legacy #config); in-page anchors like #sec-basic pass through untouched
router.beforeEach((to) => {
  const m = to.hash.match(/^#archive\/(\d+)$/);
  if (m) return { path: `/archive/${m[1]}`, hash: "" };
  if (/^#(settings|config)$/.test(to.hash)) return { path: "/settings", hash: "" };
});
