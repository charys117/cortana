<script setup>
import { computed } from "vue";
import { mdToHtml } from "../emoji";

// renders bot-message markdown the way Discord would
const props = defineProps({ text: { type: String, required: true } });
const html = computed(() => mdToHtml(props.text));
</script>

<template>
  <div class="preview" v-html="html" />
</template>

<style scoped>
.preview {
  background: var(--el-bg-color);
  border-left: 4px solid var(--el-color-primary);
  border-radius: 4px;
  padding: 12px 14px;
  font-size: 15px;
  line-height: 1.45;
  word-break: break-all;
}
</style>
