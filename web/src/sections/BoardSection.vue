<script setup>
import { reactive } from "vue";
import { formatUnits } from "../emoji";
import { members, store } from "../store";
import { pickEmoji } from "../picker";
import Field from "../components/Field.vue";
import EmojiButton from "../components/EmojiButton.vue";
import ChannelSelect from "../components/ChannelSelect.vue";
import DiscordPreview from "../components/DiscordPreview.vue";

const previewAmount = reactive({}); // user -> number

function avatar(user) {
  return members.value.find((m) => m.name === user)?.avatar;
}

function previewText(b, user) {
  const total = Number(previewAmount[user] ?? 66) || 0;
  return `${b.title}\n${formatUnits(b.units, total)}${total}`;
}

async function addUnit(b) {
  const v = await pickEmoji();
  if (v !== null) b.units.push(v);
}
</script>

<template>
  <section id="sec-board">
    <h2>积分板 Board · /record /bonus /done</h2>
    <div class="hint desc">
      每人一块积分板: bot 在指定频道维护一条消息, 用 emoji 按十进制位显示积分。units
      第 1 项代表 ×1, 第 2 项代表 ×10, 以此类推。悬赏奖励使用 ×1 的 emoji。
    </div>
    <div class="grid">
      <el-card v-for="(b, user) in store.config.board" :key="user">
        <div class="head">
          <img v-if="avatar(user)" class="avatar" :src="avatar(user)" alt="" />
          <span class="name">{{ user }} 的积分板</span>
        </div>
        <div class="row">
          <Field label="频道">
            <ChannelSelect v-model="b.channel" />
          </Field>
          <Field label="标题">
            <el-input v-model="b.title" class="w160" />
          </Field>
          <Field label="积分名称">
            <el-input v-model="b.response" class="w120" />
          </Field>
        </div>
        <Field label="积分单位">
          <div>
            <div v-for="(u, i) in b.units" :key="i" class="unit-row">
              <span class="place">×{{ 10 ** i }}</span>
              <EmojiButton v-model="b.units[i]" show-raw />
              <el-button
                v-if="b.units.length > 1"
                type="danger"
                text
                size="small"
                @click="b.units.splice(i, 1)"
              >
                移除
              </el-button>
            </div>
            <el-button v-if="b.units.length < 4" size="small" @click="addUnit(b)">
              + 添加 ×{{ 10 ** b.units.length }} 单位
            </el-button>
          </div>
        </Field>
        <div class="pv">
          <Field label="预览积分值">
            <el-input-number
              :model-value="previewAmount[user] ?? 66"
              :min="0"
              controls-position="right"
              class="w120"
              @update:model-value="previewAmount[user] = $event"
            />
          </Field>
          <DiscordPreview :text="previewText(b, user)" />
        </div>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.desc { margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
.head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.avatar { width: 28px; height: 28px; border-radius: 50%; }
.name { font-weight: 600; }
.row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; align-items: flex-end; }
.w160 { width: 160px; }
.w120 { width: 120px; }
.unit-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.place {
  width: 44px;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  text-align: right;
}
.pv { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
</style>
