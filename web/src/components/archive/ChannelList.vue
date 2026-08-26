<script setup>
import { computed } from "vue";
import { arc, openChannel } from "../../archive";

const isThread = (c) => c.type.includes("thread");

// top-level channels with their threads nested; threads whose parent row is
// missing from the archive fall back to a trailing "其他子区" group
const grouped = computed(() => {
  const tops = arc.channels.filter((c) => !isThread(c));
  const topIds = new Set(tops.map((c) => c.id));
  const byParent = {};
  const orphans = [];
  for (const t of arc.channels.filter(isThread)) {
    if (t.parent_id && topIds.has(t.parent_id)) {
      (byParent[t.parent_id] ??= []).push(t);
    } else {
      orphans.push(t);
    }
  }
  return { tops, byParent, orphans };
});

function fmtCount(n) {
  if (!n) return "";
  return n >= 10000 ? (n / 10000).toFixed(1) + "w" : String(n);
}
</script>

<template>
  <nav class="chan-list">
    <template v-for="c in grouped.tops" :key="c.id">
      <a
        class="chan"
        :class="{ active: c.id === arc.currentChannelId, empty: !c.message_count }"
        :href="'/' + c.id"
        @click.prevent="openChannel(c.id)"
      >
        <span class="glyph">#</span>
        <span class="name">{{ c.name }}</span>
        <span class="count">{{ fmtCount(c.message_count) }}</span>
      </a>
      <a
        v-for="t in grouped.byParent[c.id] || []"
        :key="t.id"
        class="chan thread"
        :class="{ active: t.id === arc.currentChannelId, empty: !t.message_count }"
        :href="'/' + t.id"
        @click.prevent="openChannel(t.id)"
      >
        <span class="glyph">└</span>
        <span class="name">{{ t.name }}</span>
        <span class="count">{{ fmtCount(t.message_count) }}</span>
      </a>
    </template>

    <template v-if="grouped.orphans.length">
      <div class="group-label">其他子区</div>
      <a
        v-for="t in grouped.orphans"
        :key="t.id"
        class="chan"
        :class="{ active: t.id === arc.currentChannelId, empty: !t.message_count }"
        :href="'/' + t.id"
        @click.prevent="openChannel(t.id)"
      >
        <span class="glyph">🧵</span>
        <span class="name">{{ t.name }}</span>
        <span class="count">{{ fmtCount(t.message_count) }}</span>
      </a>
    </template>

    <el-empty
      v-if="arc.channelsLoaded && !arc.channels.length"
      description="归档中还没有频道"
      :image-size="60"
    />
  </nav>
</template>

<style scoped>
.chan-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 0 8px;
}
.chan {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  user-select: none;
  text-decoration: none;
}
.chan:hover { background: var(--ctn-hover); color: var(--el-text-color-primary); }
.chan.active { background: var(--ctn-hover); color: var(--el-text-color-primary); }
.chan.empty { opacity: 0.5; }
.chan.thread { padding-left: 22px; font-size: 13px; }
.glyph { color: var(--el-text-color-placeholder); flex-shrink: 0; }
.name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.count { font-size: 11px; color: var(--el-text-color-placeholder); }
.group-label {
  margin: 12px 8px 2px;
  font-size: 11px;
  text-transform: uppercase;
  color: var(--el-text-color-placeholder);
}
</style>
