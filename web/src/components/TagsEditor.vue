<script setup>
import { nextTick, ref } from "vue";

// closable tag list + inline "add" input (mutates the array via v-model)
const props = defineProps({
  modelValue: { type: Array, required: true },
  placeholder: { type: String, default: "+ 添加" },
});
const emit = defineEmits(["update:modelValue"]);

const adding = ref(false);
const draft = ref("");
const inputRef = ref(null);

function remove(i) {
  const next = props.modelValue.slice();
  next.splice(i, 1);
  emit("update:modelValue", next);
}

async function startAdd() {
  adding.value = true;
  await nextTick();
  inputRef.value?.focus();
}

function confirmAdd() {
  const v = draft.value.trim();
  if (v) emit("update:modelValue", [...props.modelValue, v]);
  draft.value = "";
  adding.value = false;
}
</script>

<template>
  <div class="tags">
    <el-tag
      v-for="(t, i) in modelValue"
      :key="t + i"
      closable
      @close="remove(i)"
    >
      {{ t }}
    </el-tag>
    <el-input
      v-if="adding"
      ref="inputRef"
      v-model="draft"
      class="tag-input"
      size="small"
      :placeholder="placeholder"
      @keydown.enter="confirmAdd"
      @blur="confirmAdd"
    />
    <el-button v-else size="small" @click="startAdd">{{ placeholder }}</el-button>
  </div>
</template>

<style scoped>
.tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.tag-input { width: 140px; }
</style>
