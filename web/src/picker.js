import { reactive } from "vue";

// Singleton state for the emoji picker dialog (mounted once in App.vue).
export const pickerState = reactive({
  visible: false,
  resolve: null,
});

// Opens the picker; resolves with the chosen emoji value or null if dismissed.
export function pickEmoji() {
  return new Promise((resolve) => {
    if (pickerState.resolve) pickerState.resolve(null);
    pickerState.resolve = resolve;
    pickerState.visible = true;
  });
}
