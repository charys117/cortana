<script setup>
import { computed, ref, watch } from "vue";
import { SHORTCODES } from "../emoji";
import { pickerState } from "../picker";
import { store } from "../store";

const tab = ref("guild");
const query = ref("");
const manual = ref("");

watch(
  () => pickerState.visible,
  (v) => {
    if (v) {
      tab.value = "guild";
      query.value = "";
      manual.value = "";
    }
  },
);

const guildEmojis = computed(() => {
  const list = store.guild?.emojis ?? [];
  const q = query.value.trim().toLowerCase();
  return q ? list.filter((e) => e.name.toLowerCase().includes(q)) : list;
});

const unicodeEmojis = computed(() => {
  const q = query.value.trim().toLowerCase();
  return Object.entries(SHORTCODES).filter(([n]) => !q || n.includes(q));
});

function finish(value) {
  const resolve = pickerState.resolve;
  pickerState.resolve = null;
  pickerState.visible = false;
  resolve?.(value);
}

function onClosed() {
  // dismissed via mask / esc
  if (pickerState.resolve) {
    pickerState.resolve(null);
    pickerState.resolve = null;
  }
}
</script>

<template>
  <el-dialog
    v-model="pickerState.visible"
    title="选择表情"
    width="540px"
    append-to-body
    @closed="onClosed"
  >
    <el-tabs v-model="tab">
      <el-tab-pane label="服务器表情" name="guild">
        <el-input v-model="query" placeholder="搜索服务器表情…" clearable class="search" />
        <div v-if="guildEmojis.length" class="grid">
          <button
            v-for="e in guildEmojis"
            :key="e.id"
            :title="e.name"
            class="cell"
            @click="finish(e.code)"
          >
            <img :src="e.url" :alt="e.name" />
          </button>
        </div>
        <el-empty
          v-else
          :description="store.guild ? '没有匹配的表情' : 'bot 未连接, 服务器表情不可用'"
          :image-size="60"
        />
      </el-tab-pane>

      <el-tab-pane label="常用 Emoji" name="unicode">
        <el-input v-model="query" placeholder="搜索 (按名称, 如 heart)…" clearable class="search" />
        <div class="grid">
          <button
            v-for="[n, ch] in unicodeEmojis"
            :key="n"
            :title="':' + n + ':'"
            class="cell txt"
            @click="finish(':' + n + ':')"
          >
            {{ ch }}
          </button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="手动输入" name="manual">
        <div class="manual">
          <div class="hint">直接输入 emoji 字符、:shortcode: 或 &lt;:name:id&gt;</div>
          <el-input
            v-model="manual"
            placeholder="例如 🎲 或 :fire: 或 <:fate:9765…>"
            @keydown.enter="manual.trim() && finish(manual.trim())"
          />
          <el-button
            type="primary"
            :disabled="!manual.trim()"
            @click="finish(manual.trim())"
          >
            确定
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<style scoped>
.search { margin-bottom: 10px; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(48px, 1fr));
  gap: 4px;
  max-height: 46vh;
  overflow-y: auto;
}
.cell {
  background: none;
  border: none;
  border-radius: 6px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}
.cell:hover { background: var(--ctn-hover); }
.cell img { width: 32px; height: 32px; }
.cell.txt { font-size: 26px; }
.manual { display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
.manual .el-input { width: 100%; }
</style>
