<script setup>
import { computed } from "vue";
import { toHex } from "../emoji";

// config stores colors as integers; the picker speaks hex
const props = defineProps({ modelValue: { type: Number, default: 0 } });
const emit = defineEmits(["update:modelValue"]);

const hex = computed({
  get: () => toHex(props.modelValue),
  set: (v) => {
    const m = String(v || "").trim().replace(/^#/, "");
    if (/^[0-9a-fA-F]{6}$/.test(m)) emit("update:modelValue", parseInt(m, 16));
  },
});
</script>

<template>
  <div class="color-field">
    <el-color-picker v-model="hex" />
    <el-input v-model="hex" class="hex" />
  </div>
</template>

<style scoped>
.color-field { display: flex; gap: 6px; align-items: center; }
.hex { width: 100px; }
</style>
