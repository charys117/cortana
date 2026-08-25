<script setup>
import { store } from "../store";
import Field from "../components/Field.vue";
import ChannelSelect from "../components/ChannelSelect.vue";
import MemberSelect from "../components/MemberSelect.vue";

if (!store.config.pair) store.config.pair = [];
</script>

<template>
  <section id="sec-basic">
    <h2>基础设置</h2>
    <el-card class="card">
      <div class="row">
        <Field label="服务器名称">
          <el-input v-model="store.config.guild" class="w160" />
        </Field>
        <Field label="服务器 ID">
          <el-input v-model="store.config.guild_id" class="w200" />
        </Field>
        <Field label="时区 (UTC 偏移, 重启生效)">
          <el-input-number v-model="store.config.timezone" controls-position="right" class="w120" />
        </Field>
      </div>
      <div class="row">
        <Field label="用户 A">
          <MemberSelect v-model="store.config.pair[0]" />
        </Field>
        <Field label="用户 B">
          <MemberSelect v-model="store.config.pair[1]" />
        </Field>
      </div>
      <div class="hint">pair: 参与积分/悬赏/通知的两位成员, 互为对方的接收者</div>
    </el-card>

    <el-card class="card">
      <div class="head">每日任务与归档</div>
      <div class="row">
        <Field v-if="store.config.daily" label="每日播报频道">
          <ChannelSelect v-model="store.config.daily.channel" />
        </Field>
        <template v-if="store.config.archive">
          <Field label="媒体存储目录">
            <el-input v-model="store.config.archive.media_root" class="w180" />
          </Field>
          <Field label="下载并发数">
            <el-input-number
              v-model="store.config.archive.download_concurrency"
              controls-position="right"
              class="w160"
            />
          </Field>
        </template>
      </div>
      <div class="hint">消息归档到 PostgreSQL (连接串走 DATABASE_URL 环境变量), 附件二进制存到媒体目录</div>
    </el-card>
  </section>
</template>

<style scoped>
.card { margin-bottom: 12px; }
.head { font-weight: 600; margin-bottom: 12px; }
.row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; align-items: flex-end; }
.w120 { width: 120px; }
.w160 { width: 160px; }
.w180 { width: 180px; }
.w200 { width: 200px; }
</style>
