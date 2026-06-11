<script setup>
defineProps({
  models: { type: Array, default: () => [] },
  model: { type: String, default: '' },
  canRun: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:model', 'run'])

function modelOptionLabel(option) {
  if (option.usage_limit === null || option.usage_limit === undefined) {
    return option.name
  }
  return `${option.name} (${option.remaining ?? 0}/${option.usage_limit})`
}
</script>

<template>
  <div class="mb-5 flex flex-wrap items-center gap-3">
    <div class="flex items-center gap-2">
      <label class="text-base text-gray-500">Модель:</label>
      <select
        :value="model"
        class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
        @change="$emit('update:model', $event.target.value)"
      >
        <option v-for="option in models" :key="option.id" :value="option.id">
          {{ modelOptionLabel(option) }}
        </option>
      </select>
    </div>
    <button
      :disabled="!canRun || loading"
      class="rounded-lg bg-blue-600 px-5 py-2 text-base font-medium text-white transition-all hover:bg-blue-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
      @click="$emit('run')"
    >
      {{ loading ? 'Проверяем...' : 'Запустить проверку' }}
    </button>
  </div>
</template>
