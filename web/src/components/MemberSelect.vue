<script setup>
import { computed } from "vue";
import { members } from "../store";

const props = defineProps({ modelValue: { type: String, default: "" } });
defineEmits(["update:modelValue"]);

const missing = computed(
  () => props.modelValue && !members.value.some((m) => m.name === props.modelValue),
);
</script>

<template>
  <el-select
    :model-value="modelValue"
    filterable
    placeholder="选择成员"
    class="member"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-option
      v-if="missing"
      :value="modelValue"
      :label="modelValue + ' (不在服务器)'"
    />
    <el-option
      v-for="m in members"
      :key="m.id"
      :value="m.name"
      :label="`${m.display_name} (${m.name})`"
    >
      <span class="member-tag">
        <img :src="m.avatar" alt="" />
        {{ m.display_name }} ({{ m.name }})
      </span>
    </el-option>
  </el-select>
</template>

<style scoped>
.member { width: 220px; }
.member-tag { display: inline-flex; align-items: center; gap: 6px; }
.member-tag img { width: 22px; height: 22px; border-radius: 50%; }
</style>
