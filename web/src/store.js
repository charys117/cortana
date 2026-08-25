import { computed, reactive } from "vue";
import { ElMessage } from "element-plus";
import { getConfig, getGuild, putConfig } from "./api";

export const store = reactive({
  config: null, // editable copy, mutated in place by sections
  savedJson: "", // snapshot of the last saved state for dirty check
  guild: null, // /api/guild payload; null while the bot is offline
  loading: true,
  error: "",
});

export const dirty = computed(
  () => !!store.config && JSON.stringify(store.config) !== store.savedJson,
);

export const channels = computed(() => store.guild?.channels ?? []);
export const members = computed(() =>
  (store.guild?.members ?? []).filter((m) => !m.bot),
);

export async function load() {
  store.loading = true;
  store.error = "";
  try {
    const [c, g] = await Promise.all([getConfig(), getGuild().catch(() => null)]);
    store.config = c.config;
    store.savedJson = JSON.stringify(c.config);
    store.guild = g;
  } catch (e) {
    store.error = e.message;
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
    ElMessage.error("保存失败: " + e.message);
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
