<script setup>
import { channels, renameKey, store } from "../store";
import Field from "../components/Field.vue";
import ChannelSelect from "../components/ChannelSelect.vue";
import TagsEditor from "../components/TagsEditor.vue";

// both rule sets share the same shape: { channelName: [patterns] }
const groups = [
  {
    key: "archive_keyword",
    title: "关键词归档 (带附件的消息命中关键词后转发到对应频道)",
    label: "关键词",
    placeholder: "+ 回车添加",
    addText: "+ 新增归档规则",
  },
  {
    key: "archive_embed",
    title: "链接归档 (消息含指定前缀的链接时转发 embed)",
    label: "URL 前缀",
    placeholder: "+ https://…",
    addText: "+ 新增链接规则",
  },
];

function setChannel(cfgKey, oldCh, newCh) {
  const rules = store.config[cfgKey];
  if (newCh === oldCh || rules[newCh]) return;
  store.config[cfgKey] = renameKey(rules, oldCh, newCh);
}

function addRule(cfgKey) {
  const rules = store.config[cfgKey];
  const free = channels.value.find((c) => !rules[c.name]);
  rules[free ? free.name : "channel"] = [];
}
</script>

<template>
  <section id="sec-archive">
    <h2>自动归档 · #chat 关键词/链接分流</h2>
    <el-card v-for="g in groups" :key="g.key" class="card">
      <div class="head">{{ g.title }}</div>
      <template v-if="store.config[g.key]">
        <div v-for="(patterns, ch) in store.config[g.key]" :key="ch" class="row">
          <Field label="目标频道">
            <ChannelSelect
              :model-value="ch"
              @update:model-value="setChannel(g.key, ch, $event)"
            />
          </Field>
          <Field :label="g.label" class="patterns">
            <TagsEditor
              :model-value="patterns"
              :placeholder="g.placeholder"
              @update:model-value="store.config[g.key][ch] = $event"
            />
          </Field>
          <el-popconfirm
            :title="`删除 #${ch} 的规则?`"
            confirm-button-text="删除"
            cancel-button-text="取消"
            confirm-button-type="danger"
            @confirm="delete store.config[g.key][ch]"
          >
            <template #reference>
              <el-button type="danger" text size="small" class="del">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>
      <el-button size="small" @click="addRule(g.key)">{{ g.addText }}</el-button>
    </el-card>
  </section>
</template>

<style scoped>
.card { margin-bottom: 12px; }
.head { font-weight: 600; margin-bottom: 12px; }
/* tags wrap inside their own field, so the row itself never wraps and the
   delete button stays pinned to the right of the rule it belongs to */
.row { display: flex; gap: 14px; margin-bottom: 12px; align-items: flex-end; }
.row .patterns { flex: 1; min-width: 0; }
.row .del { margin-bottom: 4px; }
</style>
