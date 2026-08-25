<script setup>
import { computed } from "vue";
import { emojiHtml } from "../emoji";
import { pickEmoji } from "../picker";

const props = defineProps({
  modelValue: { type: String, default: "" },
  showRaw: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const html = computed(() => emojiHtml(props.modelValue));

async function choose() {
  const v = await pickEmoji();
  if (v !== null) emit("update:modelValue", v);
}
</script>

<template>
  <button type="button" class="emoji-btn" @click="choose">
    <span v-html="html" />
    <span v-if="showRaw && modelValue" class="raw">{{ modelValue }}</span>
  </button>
</template>

<style scoped>
.emoji-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: var(--ctn-input);
  border: 1px solid var(--el-border-color);
  color: var(--el-text-color-primary);
  min-width: 44px;
  height: 32px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 18px;
  cursor: pointer;
}
.emoji-btn:hover { border-color: var(--el-color-primary); }
.emoji-btn :deep(img.em) { width: 22px; height: 22px; }
.raw {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
