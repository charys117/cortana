<script setup>
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";

// Renaming an object key: edits a local draft, commits on change (enter/blur),
// reverts when the new name is empty or already taken.
const props = defineProps({
  modelValue: { type: String, required: true },
  taken: { type: Function, required: true }, // (name) => boolean
  width: { type: String, default: "160px" },
});
const emit = defineEmits(["rename"]);

const draft = ref(props.modelValue);
watch(() => props.modelValue, (v) => (draft.value = v));

function commit() {
  const nk = draft.value.trim();
  if (nk === props.modelValue) {
    draft.value = props.modelValue;
    return;
  }
  if (!nk || props.taken(nk)) {
    ElMessage.warning(nk ? `「${nk}」已存在` : "名称不能为空");
    draft.value = props.modelValue;
    return;
  }
  emit("rename", nk);
}
</script>

<template>
  <el-input v-model="draft" :style="{ width }" @change="commit" />
</template>
