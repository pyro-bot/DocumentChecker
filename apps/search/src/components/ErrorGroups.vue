<script setup>
import { bySev, severityOrder, sevBorderClass, sevEmoji } from '../utils/checkPresentation.js'

defineProps({
  groupedErrors: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-for="(group, key) in groupedErrors" :key="key">
      <div v-if="group.errors.length" class="overflow-hidden rounded-xl border border-gray-100">
        <button
          class="w-full flex items-center justify-between bg-gray-50 px-4 py-3 text-left text-base font-medium transition-colors hover:bg-gray-100"
          @click="group.open = !group.open"
        >
          <span class="flex items-center gap-2">
            {{ group.label }}
            <span class="rounded-full bg-gray-200 px-2 py-0.5 text-lg font-normal text-gray-600">
              {{ group.errors.length }}
            </span>
          </span>
          <span class="text-lg text-gray-400">{{ group.open ? '▲' : '▼' }}</span>
        </button>

        <div v-if="group.open" class="flex flex-col gap-2 bg-white p-3">
          <template v-for="severity in severityOrder" :key="severity">
            <template v-if="bySev(group.errors, severity).length">
              <div class="mt-1 text-lg font-semibold uppercase tracking-widest text-gray-400">
                {{ sevEmoji(severity) }} {{ severity }}
              </div>
              <div
                v-for="error in bySev(group.errors, severity)"
                :key="error.description"
                class="rounded-lg border border-l-4 border-gray-100 bg-gray-50 px-3 py-2.5"
                :class="sevBorderClass(severity)"
              >
                <div class="text-base font-medium text-gray-800">{{ error.section || 'Общий' }}</div>
                <div class="mt-0.5 text-lg leading-relaxed text-gray-500">{{ error.description }}</div>
              </div>
            </template>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
