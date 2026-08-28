import { computed, reactive } from "vue";
import { clearToken, getConfig, getGuild, hasToken, putConfig } from "./api";

export const store = reactive({
  config: null, // editable copy, mutated in place by sections
  savedJson: "", // snapshot of the last saved state for dirty check
  guild: null, // /api/guild payload; null while the bot is offline
  loading: true,
  error: "",
  needToken: false, // unauthorized: show the in-page token gate
  tokenMessage: "", // extra hint on the gate (e.g. stored token expired)
});

export const dirty = computed(
  () => !!store.config && JSON.stringify(store.config) !== store.savedJson,
);

export const channels = computed(() => store.guild?.channels ?? []);
export const members = computed(() =>
  (store.guild?.members ?? []).filter((m) => !m.bot),
);

// keys the sections write into unconditionally: ensure they exist before the
// savedJson snapshot, so a sparse config neither crashes nor starts out dirty
function normalize(config) {
  config.pair ??= [];
  config.archive_keyword ??= {};
  config.archive_embed ??= {};
  config.award ??= {};
  // materialize backend defaults so the controls render the effective state
  if (config.daily) {
    config.daily.archive_notify ??= true; // absent means enabled
    config.daily.time ??= "00:00"; // HH:MM in UTC
  }
  return config;
}

export async function load() {
  store.loading = true;
  store.error = "";
  store.needToken = false;
  try {
    const [c, g] = await Promise.all([getConfig(), getGuild().catch(() => null)]);
    store.config = normalize(c.config);
    store.savedJson = JSON.stringify(store.config);
    store.guild = g;
  } catch (e) {
    if (e.auth) {
      store.needToken = true;
      store.tokenMessage = hasToken() ? "令牌无效或已过期, 请重新输入" : "";
    } else {
      store.error = e.message;
    }
  } finally {
    store.loading = false;
  }
}

export async function save() {
  try {
    await putConfig(store.config);
    store.savedJson = JSON.stringify(store.config);
    ElMessage.success("已保存并热更新");
  } catch (e) {
    if (e.auth) {
      // keep the edited config; the gate re-collects the token and the
      // caller retries the save, so nothing is lost
      clearToken();
      store.needToken = true;
      store.tokenMessage = "令牌已失效, 重新输入后将继续保存当前修改";
    } else {
      ElMessage.error("保存失败: " + e.message);
    }
  }
}

export function discard() {
  store.config = JSON.parse(store.savedJson);
}

// rename a key while keeping the object's insertion order (yaml order = UI order)
export function renameKey(obj, oldKey, newKey) {
  const entries = Object.entries(obj).map(([k, v]) => [k === oldKey ? newKey : k, v]);
  return Object.fromEntries(entries);
}
