<script setup>
defineProps({
  progress: { type: Number, default: 0 },
  label: { type: String, default: '' },
})
</script>

<template>
  <div class="mb-5">
    <div class="h-1 overflow-hidden rounded-full bg-gray-200">
      <div
        class="h-full rounded-full bg-blue-500 transition-all duration-500"
        :style="{ width: progress + '%' }"
      ></div>
    </div>
    <p class="mt-1.5 text-lg text-gray-400">{{ label }}</p>
  </div>
</template>
