<script setup>
import { computed } from "vue";
import { store } from "../store";
import Field from "../components/Field.vue";

const barkUsers = computed(() =>
  Object.keys(store.config.bark ?? {}).filter((k) => k !== "post"),
);
</script>

<template>
  <section id="sec-notify">
    <h2>通知 · Bark 推送 与 /awake</h2>
    <el-card v-if="store.config.bark" class="card">
      <div class="head">Bark 推送地址</div>
      <div v-for="user in barkUsers" :key="user" class="row">
        <Field :label="user + ' 的 Bark URL'">
          <el-input v-model="store.config.bark[user]" class="w340" />
        </Field>
      </div>
      <div v-if="store.config.bark.post" class="row">
        <Field label="推送标题">
          <el-input v-model="store.config.bark.post.title" class="w140" />
        </Field>
        <Field label="推送分组">
          <el-input v-model="store.config.bark.post.group" class="w140" />
        </Field>
        <Field label="推送图标 URL">
          <el-input v-model="store.config.bark.post.icon" class="w340" />
        </Field>
      </div>
    </el-card>
    <el-card v-if="store.config.awake_notify" class="card">
      <div class="head">/awake 醒来提醒文案</div>
      <div v-for="(_, user) in store.config.awake_notify" :key="user" class="row">
        <Field :label="'通知 ' + user + ' 时的内容'">
          <el-input v-model="store.config.awake_notify[user]" class="w340" />
        </Field>
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.card { margin-bottom: 12px; }
.head { font-weight: 600; margin-bottom: 12px; }
.row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; align-items: flex-end; }
.w140 { width: 140px; }
.w340 { width: 340px; max-width: 100%; }
</style>
