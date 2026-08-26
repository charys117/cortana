<script setup>
import { computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { arc, loadChannels, openChannel } from "../../archive";
import ChannelList from "./ChannelList.vue";
import MessageList from "./MessageList.vue";
import SearchPanel from "./SearchPanel.vue";

const route = useRoute();
const router = useRouter();

const current = computed(() =>
  arc.channels.find((c) => c.id === arc.currentChannelId),
);

// the pane error can come from the channel index or the message load;
// retry whichever failed
function retry() {
  loadChannels();
  if (arc.currentChannelId) openChannel(arc.currentChannelId);
}

onMounted(async () => {
  if (!arc.channelsLoaded) await loadChannels();
  // deep link: /<channelId>
  const id = route.params.channelId;
  if (id && id !== arc.currentChannelId) openChannel(id);
});

// URL → data: browser back/forward between /<a> and /<b>
watch(
  () => route.params.channelId,
  (id) => {
    if (route.name === "archive" && id && id !== arc.currentChannelId) openChannel(id);
  },
);

// data → URL: channel opened via ChannelList / search / reply jump
watch(
  () => arc.currentChannelId,
  (id) => {
    if (id && route.name === "archive" && route.params.channelId !== id) {
      router.push(`/${id}`);
    }
  },
);
</script>

<template>
  <div class="archive">
    <aside class="chan-side">
      <div class="brand">
        <img src="/favicon.svg" alt="" />
        <span>Cortana</span>
        <el-button
          class="brand-btn"
          text
          size="small"
          title="设置"
          @click="$router.push('/settings')"
        >
          <svg
            viewBox="0 0 24 24"
            width="17"
            height="17"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="3.2" />
            <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.08a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.08a1.7 1.7 0 0 0 1.56 1.03H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.56 1.03z" />
          </svg>
        </el-button>
      </div>
      <ChannelList />
      <div class="side-actions">
        <el-button class="wide" @click="loadChannels">刷新频道</el-button>
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
            <el-button type="primary" @click="retry">重试</el-button>
          </template>
        </el-result>
      </div>
      <MessageList v-else-if="arc.currentChannelId" />
      <div v-else class="pane-empty">
        <el-empty description="从左侧选择一个频道, 或使用右上角搜索" :image-size="110" />
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
  padding: 0 12px 12px 16px;
  font-weight: 700;
  font-size: 15px;
}
.brand img { width: 28px; height: 28px; }
.brand .brand-btn { margin-left: auto; padding: 5px 6px; color: var(--el-text-color-secondary); }
.brand .brand-btn:hover { color: var(--el-text-color-primary); }
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
