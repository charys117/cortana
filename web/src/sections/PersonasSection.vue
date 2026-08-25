<script setup>
import { ref } from "vue";
import { store } from "../store";
import Field from "../components/Field.vue";
import EmojiButton from "../components/EmojiButton.vue";
import ColorField from "../components/ColorField.vue";

const addOpen = ref(false);
const addName = ref("");

function addPersona() {
  const name = addName.value.trim();
  if (!name || !/^[a-z0-9_]+$/.test(name) || store.config.cortana[name]) return;
  store.config.cortana[name] = {
    display_name: name,
    color: 5793266,
    online: "已上线",
    offline: "已下线",
  };
  addName.value = "";
  addOpen.value = false;
}

function removePersona(name) {
  delete store.config.cortana[name];
}
</script>

<template>
  <section id="sec-personas">
    <h2>Bot 形象 · /shift 切换</h2>
    <el-card v-for="(p, name) in store.config.cortana" :key="name" class="persona">
      <div class="head">
        <img class="avatar" :src="'/avatars/' + name" :alt="name" @error="$event.target.style.display = 'none'" />
        <span class="name">{{ name }}</span>
        <el-popconfirm
          :title="`删除形象 ${name}?`"
          confirm-button-text="删除"
          cancel-button-text="取消"
          confirm-button-type="danger"
          @confirm="removePersona(name)"
        >
          <template #reference>
            <el-button type="danger" text size="small" class="del">删除</el-button>
          </template>
        </el-popconfirm>
      </div>
      <div class="row">
        <Field label="显示名称">
          <el-input v-model="p.display_name" class="w160" />
        </Field>
        <Field label="主题色">
          <ColorField v-model="p.color" />
        </Field>
        <Field label="对应表情 (emoji 映射中同名条目)">
          <EmojiButton
            :model-value="store.config.emoji[name] ?? ''"
            show-raw
            @update:model-value="store.config.emoji[name] = $event"
          />
        </Field>
      </div>
      <div class="row">
        <Field label="上线台词">
          <el-input v-model="p.online" class="w300" />
        </Field>
        <Field label="下线台词">
          <el-input v-model="p.offline" class="w300" />
        </Field>
      </div>
      <div class="hint">
        头像文件: src/assets/avatars/{{ name }}.jpg (更换头像需替换文件并重新部署)
      </div>
    </el-card>

    <el-popover v-model:visible="addOpen" width="280" trigger="click">
      <template #reference>
        <el-button>+ 新增形象</el-button>
      </template>
      <div class="add-form">
        <div class="hint">
          形象标识 (小写英文), 同时需要提供 src/assets/avatars/&lt;名字&gt;.jpg
        </div>
        <el-input v-model="addName" placeholder="例如 rin" @keydown.enter="addPersona" />
        <el-button type="primary" size="small" :disabled="!addName.trim()" @click="addPersona">
          添加
        </el-button>
      </div>
    </el-popover>
  </section>
</template>

<style scoped>
.persona { margin-bottom: 12px; }
.head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; }
.name { font-weight: 600; font-size: 15px; }
.del { margin-left: auto; }
.row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 10px; align-items: flex-end; }
.w160 { width: 160px; }
.w300 { width: 300px; }
.add-form { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
</style>
