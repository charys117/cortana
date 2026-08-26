<script setup>
import { reactive } from "vue";
import { emojiHtml } from "../emoji";
import { renameKey, store } from "../store";
import Field from "../components/Field.vue";
import ColorField from "../components/ColorField.vue";
import KeyInput from "../components/KeyInput.vue";

const addState = reactive({}); // user -> { open, name }

function st(user) {
  if (!addState[user]) addState[user] = { open: false, name: "" };
  return addState[user];
}

function addTitle(user, titles) {
  const t = st(user).name.trim();
  if (!t || titles[t]) return;
  titles[t] = [Object.keys(store.config.emoji)[0] || "", 5793266];
  st(user).name = "";
  st(user).open = false;
}
</script>

<template>
  <section id="sec-award">
    <h2>授勋 Award · !award 称号徽章</h2>
    <div class="hint desc">
      每人配置一组可颁发的称号, 每个称号带表情 (引用 Emoji 映射的条目名) 与徽章颜色。
    </div>
    <el-card v-for="(titles, user) in store.config.award" :key="user" class="card">
      <div class="head">{{ user }} 可颁发的称号</div>
      <div v-for="(pair, title) in titles" :key="title" class="row">
        <Field label="称号">
          <KeyInput
            :model-value="title"
            width="130px"
            :taken="(n) => titles[n] !== undefined"
            @rename="store.config.award[user] = renameKey(titles, title, $event)"
          />
        </Field>
        <Field label="表情">
          <el-select v-model="pair[0]" class="w150" filterable>
            <el-option v-for="(_, k) in store.config.emoji" :key="k" :value="k" :label="k" />
          </el-select>
        </Field>
        <span class="icon" v-html="emojiHtml(store.config.emoji[pair[0]])" />
        <Field label="徽章颜色">
          <ColorField v-model="pair[1]" />
        </Field>
        <el-popconfirm
          :title="`删除称号「${title}」?`"
          confirm-button-text="删除"
          cancel-button-text="取消"
          confirm-button-type="danger"
          @confirm="delete titles[title]"
        >
          <template #reference>
            <el-button type="danger" text size="small">删除</el-button>
          </template>
        </el-popconfirm>
      </div>

      <el-popover v-model:visible="st(user).open" width="240" trigger="click">
        <template #reference>
          <el-button size="small">+ 新增称号</el-button>
        </template>
        <div class="add-form">
          <el-input
            v-model="st(user).name"
            placeholder="称号名称"
            @keydown.enter="addTitle(user, titles)"
          />
          <el-button
            type="primary"
            size="small"
            :disabled="!st(user).name.trim()"
            @click="addTitle(user, titles)"
          >
            添加
          </el-button>
        </div>
      </el-popover>
    </el-card>
  </section>
</template>

<style scoped>
.desc { margin-bottom: 12px; }
.card { margin-bottom: 12px; }
.head { font-weight: 600; margin-bottom: 12px; }
.row { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 10px; align-items: flex-end; }
.w150 { width: 150px; }
.icon { align-self: flex-end; padding-bottom: 4px; }
.add-form { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.add-form .el-input { width: 100%; }
</style>
