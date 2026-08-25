<script setup>
defineProps({ label: { type: String, default: "" } });
</script>

<template>
  <div class="field">
    <label v-if="label">{{ label }}</label>
    <slot />
  </div>
</template>

<style scoped>
.field { display: flex; flex-direction: column; gap: 4px; }
.field > label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: 600;
}
</style>
