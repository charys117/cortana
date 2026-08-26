<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import { setToken } from "./api";
import { dirty, discard, load, save, store } from "./store";
import EmojiPicker from "./components/EmojiPicker.vue";
import PersonasSection from "./sections/PersonasSection.vue";
import EmojiSection from "./sections/EmojiSection.vue";
import BoardSection from "./sections/BoardSection.vue";
import AwardSection from "./sections/AwardSection.vue";
import NotifySection from "./sections/NotifySection.vue";
import ArchiveSection from "./sections/ArchiveSection.vue";
import BasicSection from "./sections/BasicSection.vue";

const NAV = [
  ["personas", "Bot 形象"],
  ["emoji", "Emoji 映射"],
  ["board", "积分板 Board"],
  ["award", "授勋 Award"],
  ["notify", "通知 Bark"],
  ["archive", "自动归档"],
  ["basic", "基础设置"],
];

const saving = ref(false);
const activeSec = ref("personas");

// --- in-page token gate (replaces the old blocking prompt()) ---
const tokenInput = ref("");

function submitToken() {
  const v = tokenInput.value.trim();
  if (!v) return;
  setToken(v);
  tokenInput.value = "";
  store.needToken = false;
  store.tokenMessage = "";
  // token expired mid-session: the edits are still in store.config, retry the
  // save instead of reloading over them
  if (store.config && dirty.value) doSave();
  else load();
}

async function doSave() {
  saving.value = true;
  try {
    await save();
  } finally {
    saving.value = false;
  }
}

async function reload() {
  if (dirty.value) {
    try {
      await ElMessageBox.confirm("重新加载将丢弃当前未保存的修改。", "放弃修改?", {
        confirmButtonText: "丢弃并重新加载",
        cancelButtonText: "取消",
        type: "warning",
      });
    } catch {
      return;
    }
  }
  load();
}

function onScroll() {
  if (!store.config) return;
  let cur = NAV[0][0];
  for (const [id] of NAV) {
    const el = document.getElementById("sec-" + id);
    if (el && el.getBoundingClientRect().top <= 120) cur = id;
  }
  // the last section can be too short to ever cross the threshold
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 8) {
    cur = NAV[NAV.length - 1][0];
  }
  activeSec.value = cur;
}

function beforeUnload(e) {
  if (dirty.value) e.preventDefault();
}

onMounted(() => {
  window.addEventListener("beforeunload", beforeUnload);
  window.addEventListener("scroll", onScroll, { passive: true });
  load();
});
onUnmounted(() => {
  window.removeEventListener("beforeunload", beforeUnload);
  window.removeEventListener("scroll", onScroll);
});
</script>

<template>
  <el-config-provider :locale="zhCn">
  <div class="layout">
    <aside>
      <div class="brand">
        <img src="/favicon.svg" alt="" />
        <span>Cortana 配置台</span>
      </div>
      <div v-if="store.guild || store.config" class="guild-head">
        <template v-if="store.guild">
          <img v-if="store.guild.guild.icon" :src="store.guild.guild.icon" alt="" />
          <div>
            <div class="g-name">{{ store.guild.guild.name }}</div>
            <div class="g-sub">
              {{ store.guild.emojis.length }} 个表情 · {{ store.guild.channels.length }} 个频道
            </div>
          </div>
        </template>
        <div v-else class="g-sub">⚠️ bot 未连接, 服务器数据不可用</div>
      </div>
      <nav>
        <template v-if="store.config">
          <a
            v-for="[id, label] in NAV"
            :key="id"
            :href="'#sec-' + id"
            :class="{ active: activeSec === id }"
          >
            {{ label }}
          </a>
        </template>
      </nav>
      <div class="side-actions">
        <el-button class="reload" @click="reload">重新加载</el-button>
      </div>
    </aside>

    <main>
      <div v-if="store.loading" v-loading="true" class="placeholder" element-loading-text="加载中…" />
      <div v-else-if="store.needToken" class="placeholder">
        <div class="token-gate">
          <img class="gate-logo" src="/favicon.svg" alt="" />
          <h1>需要访问令牌</h1>
          <div class="hint">CORTANA_WEB_TOKEN · 令牌保存在本浏览器 localStorage 中</div>
          <el-input
            v-model="tokenInput"
            type="password"
            show-password
            placeholder="粘贴访问令牌"
            @keydown.enter="submitToken"
          />
          <el-button type="primary" :disabled="!tokenInput.trim()" @click="submitToken">
            进入配置台
          </el-button>
          <div v-if="store.tokenMessage" class="gate-err">{{ store.tokenMessage }}</div>
        </div>
      </div>
      <div v-else-if="store.error" class="placeholder">
        <el-result icon="error" title="加载失败" :sub-title="store.error">
          <template #extra>
            <el-button type="primary" @click="load">重试</el-button>
          </template>
        </el-result>
      </div>
      <template v-else-if="store.config">
        <h1>{{ store.config.guild || "Cortana" }} 配置台</h1>
        <div class="subtitle">
          修改后点击底部「保存到集群」即时生效 · 配置保存在 PostgreSQL
        </div>
        <PersonasSection />
        <EmojiSection />
        <BoardSection />
        <AwardSection />
        <NotifySection />
        <ArchiveSection />
        <BasicSection />
      </template>
    </main>
  </div>

  <transition name="rise">
    <div v-if="dirty" class="savebar">
      <span class="msg">当前有未保存的修改</span>
      <el-button @click="discard">还原</el-button>
      <el-button type="success" :loading="saving" @click="doSave">保存到集群</el-button>
    </div>
  </transition>

  <EmojiPicker />
  </el-config-provider>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; }

aside {
  width: 232px;
  flex-shrink: 0;
  background: var(--ctn-sidebar);
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: sticky;
  top: 0;
  height: 100vh;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px 12px;
  font-weight: 700;
  font-size: 15px;
}
.brand img { width: 28px; height: 28px; }
.guild-head { display: flex; align-items: center; gap: 10px; padding: 8px 10px 16px; }
.guild-head img { width: 40px; height: 40px; border-radius: 12px; }
.g-name { font-weight: 700; }
.g-sub { font-size: 12px; color: var(--el-text-color-placeholder); }
aside nav { flex: 1; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }
aside nav a {
  color: var(--el-text-color-secondary);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 15px;
  cursor: pointer;
}
aside nav a { text-decoration: none; }
aside nav a:hover,
aside nav a.active { background: var(--ctn-hover); color: var(--el-text-color-primary); }
.side-actions { padding: 8px; }
.reload { width: 100%; }

main { flex: 1; padding: 32px 40px 120px; max-width: 980px; }
h1 { font-size: 22px; margin: 0 0 4px; }
.subtitle { color: var(--el-text-color-placeholder); font-size: 13px; margin-bottom: 28px; }
.placeholder { padding: 120px 0; }

main :deep(section) { margin-bottom: 40px; scroll-margin-top: 24px; }
main :deep(section > h2) {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color);
  padding-bottom: 8px;
  margin: 0 0 12px;
  font-weight: 600;
}

.savebar {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 24px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
  padding: 10px 12px 10px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 50;
  width: min(640px, calc(100vw - 32px));
}
.savebar .msg { flex: 1; font-size: 14px; color: var(--el-text-color-secondary); }

.rise-enter-active, .rise-leave-active { transition: all 0.2s ease; }
.rise-enter-from, .rise-leave-to { opacity: 0; transform: translate(-50%, 12px); }

.token-gate {
  max-width: 340px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: center;
}
.token-gate h1 { font-size: 18px; margin: 0; }
.gate-logo { width: 48px; height: 48px; margin: 0 auto; }
.gate-err { font-size: 13px; color: var(--el-color-danger); }

@media (max-width: 900px) {
  aside { display: none; }
  main { padding: 20px 16px 120px; }
}
</style>
