<script setup>
import { computed } from "vue";
import { arc, openChannel } from "../../archive";

const isThread = (c) => c.type.includes("thread");
const isCategory = (c) => c.type === "category";

// Discord sidebar order: position asc; null positions (threads, rows archived
// before the position column existed) fall to the end, name as tiebreak
const byPos = (a, b) =>
  (a.position ?? Infinity) - (b.position ?? Infinity) ||
  a.name.localeCompare(b.name);

// flat render list mirroring the Discord sidebar: uncategorized channels
// first, then each category as a label followed by its channels; threads
// nest under their channel, and threads whose parent row is missing from
// the archive fall back to a trailing "其他子区" group
const items = computed(() => {
  const categories = arc.channels.filter(isCategory).sort(byPos);
  const catIds = new Set(categories.map((c) => c.id));
  const tops = arc.channels
    .filter((c) => !isThread(c) && !isCategory(c))
    .sort(byPos);
  const topIds = new Set(tops.map((c) => c.id));

  const threadsByParent = {};
  const orphans = [];
  for (const t of arc.channels.filter(isThread).sort(byPos)) {
    if (t.parent_id && topIds.has(t.parent_id)) {
      (threadsByParent[t.parent_id] ??= []).push(t);
    } else {
      orphans.push(t);
    }
  }

  const out = [];
  const pushChannel = (c) => {
    out.push({ kind: "channel", c });
    for (const t of threadsByParent[c.id] || []) out.push({ kind: "thread", c: t });
  };
  for (const c of tops.filter((c) => !c.parent_id || !catIds.has(c.parent_id))) {
    pushChannel(c);
  }
  for (const cat of categories) {
    const chans = tops.filter((c) => c.parent_id === cat.id);
    if (!chans.length) continue;
    out.push({ kind: "label", c: cat });
    for (const c of chans) pushChannel(c);
  }
  if (orphans.length) {
    out.push({ kind: "label", c: { id: "orphans", name: "其他子区" } });
    for (const t of orphans) out.push({ kind: "orphan", c: t });
  }
  return out;
});

function fmtCount(n) {
  if (!n) return "";
  return n >= 10000 ? (n / 10000).toFixed(1) + "w" : String(n);
}
</script>

<template>
  <nav class="chan-list">
    <template v-for="it in items" :key="it.kind + '-' + it.c.id">
      <div v-if="it.kind === 'label'" class="group-label">{{ it.c.name }}</div>
      <a
        v-else
        class="chan"
        :class="{
          thread: it.kind === 'thread',
          active: it.c.id === arc.currentChannelId,
          empty: !it.c.message_count,
        }"
        :href="'/' + it.c.id"
        @click.prevent="openChannel(it.c.id)"
      >
        <span class="glyph">{{
          it.kind === "thread" ? "└" : it.kind === "orphan" ? "🧵" : "#"
        }}</span>
        <span class="name">{{ it.c.name }}</span>
        <span class="count">{{ fmtCount(it.c.message_count) }}</span>
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
