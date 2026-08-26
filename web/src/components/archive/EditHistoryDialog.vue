<script setup>
import { ref, watch } from "vue";
import { api } from "../../api";
import { fmtTime } from "../../archive";
import { mdToHtml } from "../../emoji";

const props = defineProps({
  message: { type: Object, default: null },
});
const emit = defineEmits(["close"]);

const versions = ref([]);
const loading = ref(false);
const error = ref("");

watch(
  () => props.message,
  async (msg) => {
    if (!msg) return;
    versions.value = [];
    error.value = "";
    loading.value = true;
    try {
      const data = await api(`/api/archive/messages/${msg.id}/versions`);
      versions.value = data.versions;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  },
);
</script>

<template>
  <el-dialog
    :model-value="!!message"
    title="编辑历史"
    width="560px"
    @close="emit('close')"
  >
    <div v-if="loading" v-loading="true" class="hist-loading" />
    <template v-else-if="message">
      <div v-if="error" class="hint">加载失败: {{ error }}</div>
      <div v-else-if="!versions.length" class="hint">
        没有记录到历史版本（编辑发生在归档之前）
      </div>
      <div v-for="(v, i) in versions" :key="i" class="version">
        <div class="v-head">
          版本 {{ i + 1 }} · 记录于 {{ fmtTime(v.captured_at) }}
        </div>
        <div class="v-content" v-html="mdToHtml(v.content || '（无文本内容）')" />
      </div>
      <div class="version current">
        <div class="v-head">当前版本 · 编辑于 {{ fmtTime(message.edited_at) }}</div>
        <div class="v-content" v-html="mdToHtml(message.content || '（无文本内容）')" />
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.hist-loading { height: 120px; }
.version {
  border-left: 3px solid var(--el-border-color);
  padding: 6px 12px;
  margin-bottom: 12px;
}
.version.current { border-left-color: var(--el-color-primary); }
.v-head { font-size: 12px; color: var(--el-text-color-placeholder); margin-bottom: 4px; }
.v-content { font-size: 14px; line-height: 1.45; word-break: break-word; }
</style>
