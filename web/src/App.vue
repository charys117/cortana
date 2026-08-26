<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { dirty, discard, load, save, store } from "./store";
import ConfigView from "./components/ConfigView.vue";
import EmojiPicker from "./components/EmojiPicker.vue";

const saving = ref(false);
const route = useRoute();

// the archive replaces the whole layout only once auth/config loading settled;
// until then the config layout (loading / token gate / error) stays up
const blocked = computed(
  () => route.name === "archive" && (store.loading || store.needToken || !!store.error),
);

async function doSave() {
  saving.value = true;
  try {
    await save();
  } finally {
    saving.value = false;
  }
}

function beforeUnload(e) {
  if (dirty.value) e.preventDefault();
}

onMounted(() => {
  window.addEventListener("beforeunload", beforeUnload);
  load();
});
onUnmounted(() => {
  window.removeEventListener("beforeunload", beforeUnload);
});
</script>

<template>
  <ConfigView v-if="blocked" />
  <router-view v-else />

  <transition name="rise">
    <div v-if="dirty" class="savebar">
      <span class="msg">当前有未保存的修改</span>
      <el-button @click="discard">还原</el-button>
      <el-button type="success" :loading="saving" @click="doSave">保存到集群</el-button>
    </div>
  </transition>

  <EmojiPicker />
</template>

<style scoped>
.savebar {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 24px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
  padding: 10px 12px 10px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 50;
  width: min(640px, calc(100vw - 32px));
}
.savebar .msg { flex: 1; font-size: 14px; color: var(--el-text-color-secondary); }

.rise-enter-active, .rise-leave-active { transition: all 0.2s ease; }
.rise-enter-from, .rise-leave-to { opacity: 0; transform: translate(-50%, 12px); }
</style>
