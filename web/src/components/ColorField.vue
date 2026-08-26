<script setup>
import { ref, watch } from "vue";
import { toHex } from "../emoji";

// config stores colors as integers; the picker speaks hex. The text input
// edits a draft committed on change, so bad input warns and reverts instead
// of being silently ignored.
const props = defineProps({ modelValue: { type: Number, default: 0 } });
const emit = defineEmits(["update:modelValue"]);

const draft = ref(toHex(props.modelValue));
watch(() => props.modelValue, (v) => (draft.value = toHex(v)));

function commit() {
  const m = String(draft.value || "").trim().replace(/^#/, "");
  if (/^[0-9a-fA-F]{6}$/.test(m)) {
    emit("update:modelValue", parseInt(m, 16));
    draft.value = "#" + m.toLowerCase();
  } else {
    ElMessage.warning(`「${draft.value}」不是有效颜色, 需要 6 位十六进制`);
    draft.value = toHex(props.modelValue);
  }
}

function pick(v) {
  if (v) emit("update:modelValue", parseInt(v.replace(/^#/, ""), 16));
}
</script>

<template>
  <div class="color-field">
    <el-color-picker :model-value="toHex(modelValue)" @update:model-value="pick" />
    <el-input v-model="draft" class="hex" @change="commit" />
  </div>
</template>

<style scoped>
.color-field { display: flex; gap: 6px; align-items: center; }
.hex { width: 100px; }
</style>
