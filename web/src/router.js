import { createRouter, createWebHistory } from "vue-router";
import ArchiveView from "./components/archive/ArchiveView.vue";
import SettingsView from "./components/SettingsView.vue";

// History mode: src/web/server.py serves index.html for /, /<channelId>,
// /settings, /config and legacy /archive* so deep links survive a refresh.
// The archive is the root: "/" lists channels, "/<channelId>" opens one;
// the config editor lives at /settings.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/:channelId(\\d+)?", name: "archive", component: ArchiveView },
    { path: "/settings", name: "settings", component: SettingsView },
    { path: "/config", redirect: "/settings" },
    // /archive URLs from the previous router generation
    {
      path: "/archive/:channelId(\\d+)?",
      redirect: (to) => "/" + (to.params.channelId || ""),
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition || { top: 0 };
  },
});

// legacy hash deep links from the pre-router UI (#archive/<id>, #settings,
// legacy #config); in-page anchors like #sec-basic pass through untouched
router.beforeEach((to) => {
  const m = to.hash.match(/^#archive\/(\d+)$/);
  if (m) return { path: `/${m[1]}`, hash: "" };
  if (/^#(settings|config)$/.test(to.hash)) return { path: "/settings", hash: "" };
});
