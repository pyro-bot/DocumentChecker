<script setup>
import { getMetrics } from '../utils/checkPresentation.js'

defineProps({
  result: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div class="mb-5 grid grid-cols-3 gap-3">
    <div
      v-for="metric in getMetrics(result)"
      :key="metric.label"
      class="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3"
    >
      <div class="mb-1 text-lg text-gray-400">{{ metric.label }}</div>
      <div class="text-2xl font-semibold text-gray-900">{{ metric.value }}</div>
    </div>
  </div>
</template>
