<script setup>
import { computed } from "vue";
import { channels, store } from "../store";

const props = defineProps({ modelValue: { type: String, default: "" } });
defineEmits(["update:modelValue"]);

const missing = computed(
  () => props.modelValue && !channels.value.some((c) => c.name === props.modelValue),
);
// bot offline just means we can't verify — don't claim the channel is gone
const missingNote = computed(() => (store.guild ? " (不存在)" : " (离线, 未验证)"));
</script>

<template>
  <el-select
    :model-value="modelValue"
    filterable
    placeholder="选择频道"
    class="chan"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-option
      v-if="missing"
      :value="modelValue"
      :label="'#' + modelValue + missingNote"
    />
    <el-option
      v-for="c in channels"
      :key="c.id"
      :value="c.name"
      :label="'#' + c.name"
    />
  </el-select>
</template>

<style scoped>
.chan { width: 180px; }
</style>
