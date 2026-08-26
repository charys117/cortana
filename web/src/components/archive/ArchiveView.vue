<script setup>
import { computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { arc, loadChannels, openChannel } from "../../archive";
import ChannelList from "./ChannelList.vue";
import MessageList from "./MessageList.vue";
import SearchPanel from "./SearchPanel.vue";

const route = useRoute();

const current = computed(() =>
  arc.channels.find((c) => c.id === arc.currentChannelId),
);

onMounted(async () => {
  if (!arc.channelsLoaded) await loadChannels();
  // deep link: /archive/<channelId>
  const id = route.params.channelId;
  if (id && id !== arc.currentChannelId) openChannel(id);
});

// browser back/forward between /archive/<a> and /archive/<b>
watch(
  () => route.params.channelId,
  (id) => {
    if (route.name === "archive" && id && id !== arc.currentChannelId) openChannel(id);
  },
);
</script>

<template>
  <div class="archive">
    <aside class="chan-side">
      <div class="brand">
        <img src="/favicon.svg" alt="" />
        <span>归档浏览</span>
      </div>
      <ChannelList />
      <div class="side-actions">
        <el-button class="wide" @click="loadChannels">刷新频道</el-button>
        <el-button class="wide" @click="$router.push('/')">← 返回配置台</el-button>
      </div>
    </aside>

    <div class="pane">
      <header class="pane-head">
        <span v-if="current" class="chan-name">
          <span class="glyph">#</span> {{ current.name }}
        </span>
        <span v-else class="hint">选择一个频道开始浏览</span>
        <span class="spacer" />
        <el-button text :type="arc.search.open ? 'primary' : ''" @click="arc.search.open = !arc.search.open">
          🔍 搜索
        </el-button>
      </header>

      <div v-if="arc.error" class="pane-err">
        <el-result icon="error" title="加载失败" :sub-title="arc.error">
          <template #extra>
            <el-button type="primary" @click="loadChannels">重试</el-button>
          </template>
        </el-result>
      </div>
      <MessageList v-else-if="arc.currentChannelId" />
      <div v-else class="pane-empty">
        <el-empty description="从左侧选择一个频道, 或使用右上角搜索" />
      </div>
    </div>

    <SearchPanel v-if="arc.search.open" />
  </div>
</template>

<style scoped>
.archive {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.chan-side {
  width: 240px;
  flex-shrink: 0;
  background: var(--ctn-sidebar);
  display: flex;
  flex-direction: column;
  padding: 16px 0 8px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px 12px;
  font-weight: 700;
  font-size: 15px;
}
.brand img { width: 28px; height: 28px; }
.side-actions {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.side-actions .wide { width: 100%; margin-left: 0; }

.pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.pane-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color);
  flex-shrink: 0;
}
.chan-name { font-weight: 700; font-size: 15px; }
.chan-name .glyph { color: var(--el-text-color-placeholder); }
.spacer { flex: 1; }
.pane-empty, .pane-err { flex: 1; display: flex; align-items: center; justify-content: center; }

@media (max-width: 900px) {
  .chan-side { width: 200px; }
  .search-panel { display: none; }
}
</style>
