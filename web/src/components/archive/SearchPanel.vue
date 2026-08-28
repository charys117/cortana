<script setup>
import { computed, onUnmounted, watch } from "vue";
import { arc, fmtTime, jumpTo, loadUsers, resetSearch, runSearch } from "../../archive";
import { esc } from "../../emoji";

const s = arc.search;
loadUsers();

const userOptions = computed(() =>
  arc.users.map((u) => ({
    id: u.id,
    label: u.display_name ? `${u.display_name} (${u.username})` : u.username,
  })),
);

// live search: debounce typing, refresh filters immediately; a query that
// drops below the minimum clears the results instead of leaving stale ones
let debounceTimer = null;
watch(
  () => [s.q, s.channelId, s.authorId, s.dateRange],
  ([q], [oldQ]) => {
    clearTimeout(debounceTimer);
    if (q.trim().length < 2) {
      resetSearch();
      return;
    }
    debounceTimer = setTimeout(() => runSearch(), q === oldQ ? 0 : 350);
  },
);
onUnmounted(() => clearTimeout(debounceTimer));

// IME composition Enter (选词) must not trigger a search
function onEnter(e) {
  if (e.isComposing || e.keyCode === 229) return;
  clearTimeout(debounceTimer);
  runSearch();
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// excerpt around the first hit, hit wrapped in <mark>; everything escaped.
// q is the executed query, so highlights stay in sync with the results.
function excerptHtml(content, q) {
  const c = (content || "").replace(/\s+/g, " ");
  const idx = q ? c.toLowerCase().indexOf(q.toLowerCase()) : -1;
  if (idx < 0) return esc(c.slice(0, 160)) + (c.length > 160 ? "…" : "");
  const start = Math.max(0, idx - 40);
  const end = Math.min(c.length, idx + q.length + 120);
  const seg = (start > 0 ? "…" : "") + c.slice(start, end) + (end < c.length ? "…" : "");
  const escaped = esc(seg);
  return escaped.replace(
    new RegExp(escapeRegExp(esc(q)), "gi"),
    (m) => `<mark>${m}</mark>`,
  );
}

function channelName(r) {
  return r.channel_name || arc.channels.find((c) => c.id === r.channel_id)?.name || "?";
}
</script>

<template>
  <aside class="search-panel">
    <div class="search-head">
      <span>搜索归档</span>
      <el-button text size="small" @click="s.open = false">✕</el-button>
    </div>
    <div class="search-form">
      <el-input
        v-model="s.q"
        placeholder="搜索消息内容 (至少2个字符)"
        clearable
        @keydown.enter="onEnter"
      >
        <template #prefix>🔍</template>
      </el-input>
      <el-select v-model="s.channelId" placeholder="全部频道" clearable filterable>
        <el-option
          v-for="c in arc.channels.filter((c) => c.type !== 'category')"
          :key="c.id"
          :label="'# ' + c.name"
          :value="c.id"
        />
      </el-select>
      <el-select v-model="s.authorId" placeholder="全部成员" clearable filterable>
        <el-option
          v-for="u in userOptions"
          :key="u.id"
          :label="u.label"
          :value="u.id"
        />
      </el-select>
      <el-date-picker
        v-model="s.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        unlink-panels
        class="date-range"
      />
      <el-button type="primary" :loading="s.loading" @click="runSearch()">搜索</el-button>
      <div v-if="s.error" class="search-err">{{ s.error }}</div>
    </div>

    <div class="results">
      <div v-if="s.searched && s.results.length" class="r-count-line">
        {{ s.results.length }}{{ s.hasMore ? "+" : "" }} 条结果
      </div>
      <div
        v-for="r in s.results"
        :key="r.id"
        class="result"
        :class="{ deleted: r.deleted_at }"
        @click="jumpTo(r.channel_id, r.id)"
      >
        <div class="r-meta">
          <span class="r-chan"># {{ channelName(r) }}</span>
          <span class="r-time">{{ fmtTime(r.created_at) }}</span>
        </div>
        <div class="r-line">
          <b>{{ r.author_name }}</b>
          <span v-if="r.deleted_at" class="r-del">已删除</span>
        </div>
        <div class="r-content" v-html="excerptHtml(r.content, s.executedQ)" />
      </div>

      <el-empty
        v-if="s.searched && !s.results.length && !s.loading"
        description="没有找到匹配的消息"
        :image-size="60"
      />
      <div v-if="!s.searched && !s.loading" class="r-hint">
        输入关键词搜索归档消息
      </div>
      <div v-if="s.hasMore" class="more">
        <el-button size="small" text :loading="s.loading" @click="runSearch(true)">
          加载更多结果
        </el-button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.search-panel {
  width: 340px;
  flex-shrink: 0;
  background: var(--ctn-sidebar);
  border-left: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.search-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 8px;
  font-weight: 700;
}
.search-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 14px 12px;
  border-bottom: 1px solid var(--el-border-color);
}
.search-err { font-size: 12px; color: var(--el-color-danger); }
.search-form :deep(.date-range) { width: 100%; }

.results { flex: 1; overflow-y: auto; padding: 8px; }
.result {
  background: var(--ctn-card);
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 8px;
  cursor: pointer;
  border-left: 3px solid transparent;
}
.result:hover { background: var(--ctn-hover); }
.result.deleted { border-left-color: var(--el-color-danger); }
.r-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  margin-bottom: 2px;
}
.r-line { font-size: 13px; margin-bottom: 2px; }
.r-del { color: var(--el-color-danger); font-size: 11px; margin-left: 6px; }
.r-content {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  word-break: break-word;
}
/* no horizontal padding: it pushes CJK glyphs apart and breaks char spacing */
.r-content :deep(mark) {
  background: rgba(240, 178, 50, 0.35);
  color: var(--el-text-color-primary);
  border-radius: 2px;
}
.r-count-line {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  padding: 2px 4px 6px;
}
.r-hint {
  text-align: center;
  padding: 32px 12px;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}
.more { text-align: center; padding: 4px 0 12px; }
</style>
