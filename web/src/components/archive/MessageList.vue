<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { arc, fmtDay, loadNewer, loadOlder } from "../../archive";
import MessageItem from "./MessageItem.vue";
import EditHistoryDialog from "./EditHistoryDialog.vue";

const box = ref(null);
const historyFor = ref(null);

const COMPACT_WINDOW = 7 * 60 * 1000; // same-author messages within 7min collapse

// group by the viewer's local date so dividers match the rendered labels
const dayKey = (m) => new Date(m.created_at).toDateString();

const rows = computed(() => {
  const out = [];
  let prev = null;
  for (const m of arc.messages) {
    if (!prev || dayKey(prev) !== dayKey(m)) {
      out.push({ key: "day-" + m.id, divider: m.created_at });
      prev = null; // day break also breaks compact grouping
    }
    const compact =
      !!prev &&
      prev.author_id === m.author_id &&
      !m.reply_to &&
      m.type === "default" &&
      prev.type === "default" &&
      new Date(m.created_at) - new Date(prev.created_at) < COMPACT_WINDOW;
    out.push({ key: m.id, msg: m, compact });
    prev = m;
  }
  return out;
});

// remount over already-loaded messages (back from settings): start at bottom
onMounted(async () => {
  if (arc.loading || !arc.messages.length) return;
  await nextTick();
  const el = box.value;
  if (el) el.scrollTop = el.scrollHeight;
});

// after a full pane load: bottom for a channel open, centered for a jump
watch(
  () => arc.loading,
  async (val, old) => {
    if (!(old && !val)) return;
    await nextTick();
    const el = box.value;
    if (!el) return;
    if (arc.jumpTarget) {
      el.querySelector(`[data-mid="${arc.jumpTarget}"]`)?.scrollIntoView({
        block: "center",
      });
      setTimeout(() => (arc.jumpTarget = ""), 2000);
    } else {
      el.scrollTop = el.scrollHeight;
    }
  },
);

// prepend without a visual jump: restore scrollTop by the height delta
async function pullOlder() {
  const el = box.value;
  if (!el) return;
  const prevHeight = el.scrollHeight;
  const prevTop = el.scrollTop;
  const n = await loadOlder();
  if (n > 0) {
    await nextTick();
    el.scrollTop = prevTop + (el.scrollHeight - prevHeight);
  }
}

function onScroll() {
  const el = box.value;
  if (!el || arc.loading || arc.loadingMore) return;
  if (el.scrollTop < 400 && arc.hasMoreBefore) {
    pullOlder();
  } else if (
    arc.hasMoreAfter &&
    el.scrollHeight - el.scrollTop - el.clientHeight < 400
  ) {
    loadNewer();
  }
}
</script>

<template>
  <div ref="box" class="mlist" @scroll.passive="onScroll">
    <div v-if="arc.loading" v-loading="true" class="pane-loading" element-loading-text="加载中…" />
    <template v-else>
      <div v-if="arc.hasMoreBefore" class="load-edge">
        <el-button size="small" text :loading="arc.loadingMore" @click="pullOlder">
          加载更早消息
        </el-button>
      </div>
      <div v-else-if="arc.messages.length" class="chan-start">已到达归档的开头</div>

      <template v-for="row in rows" :key="row.key">
        <div v-if="row.divider" class="day-divider">
          <span>{{ fmtDay(row.divider) }}</span>
        </div>
        <MessageItem
          v-else
          :msg="row.msg"
          :compact="row.compact"
          @show-history="historyFor = $event"
        />
      </template>

      <div v-if="arc.hasMoreAfter" class="load-edge">
        <el-button size="small" text :loading="arc.loadingMore" @click="loadNewer">
          加载更新消息
        </el-button>
      </div>

      <el-empty v-if="!arc.messages.length" description="该频道暂无归档消息" />
    </template>
  </div>
  <EditHistoryDialog :message="historyFor" @close="historyFor = null" />
</template>

<style scoped>
.mlist {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 24px;
  min-height: 0;
}
.pane-loading { height: 100%; }
.load-edge { text-align: center; padding: 10px 0; }
.chan-start {
  text-align: center;
  padding: 18px 0 6px;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}
.day-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 16px 4px;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}
.day-divider::before,
.day-divider::after {
  content: "";
  flex: 1;
  border-top: 1px solid var(--el-border-color);
}
</style>
