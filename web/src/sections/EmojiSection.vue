<script setup>
import { renameKey, store } from "../store";
import EmojiButton from "../components/EmojiButton.vue";
import KeyInput from "../components/KeyInput.vue";

function addEntry() {
  let n = "new_emoji";
  let i = 1;
  while (store.config.emoji[n] !== undefined) n = "new_emoji_" + i++;
  store.config.emoji[n] = "";
}
</script>

<template>
  <section id="sec-emoji">
    <h2>Emoji 映射 · 供形象/授勋/归档引用</h2>
    <el-card>
      <div class="rows">
        <div v-for="(v, key) in store.config.emoji" :key="key" class="row">
          <KeyInput
            :model-value="key"
            :taken="(n) => store.config.emoji[n] !== undefined"
            @rename="store.config.emoji = renameKey(store.config.emoji, key, $event)"
          />
          <EmojiButton v-model="store.config.emoji[key]" show-raw />
          <el-popconfirm
            :title="`删除条目 ${key}? 引用它的形象/称号会失效`"
            confirm-button-text="删除"
            cancel-button-text="取消"
            confirm-button-type="danger"
            width="260"
            @confirm="delete store.config.emoji[key]"
          >
            <template #reference>
              <el-button type="danger" text size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
      <el-button size="small" @click="addEntry">+ 新增条目</el-button>
    </el-card>
  </section>
</template>

<style scoped>
.rows {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 0 24px;
}
.row { display: flex; gap: 12px; align-items: center; margin-bottom: 10px; }
</style>
