<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const models = computed(() => store.state.models)
const model = computed(() => store.state.model)
const currentUser = computed(() => store.state.currentUser)
const usageResetIntervalHours = computed(() => store.state.usageResetIntervalHours)
const canRun = computed(() => store.getters.canRun)
const loading = computed(() => store.state.loading)

const usageResetInfo = computed(() => {
  const interval = usageResetIntervalHours.value
  if (!interval || currentUser.value?.role === 'admin') {
    return ''
  }

  return `Лимиты сбрасываются каждые ${formatHours(interval)}`
})

function formatHours(value) {
  const hours = Number(value)
  if (!Number.isFinite(hours)) {
    return `${value} ч.`
  }

  const formatted = Number.isInteger(hours) ? String(hours) : hours.toFixed(1).replace(/\.0$/, '')
  return `${formatted} ч.`
}

function modelOptionLabel(option) {
  if (option.usage_limit === null || option.usage_limit === undefined) {
    return option.name
  }
  return `${option.name} (${option.remaining ?? 0}/${option.usage_limit})`
}
</script>

<template>
  <div class="mb-5 flex flex-wrap items-center gap-3">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
      <div class="flex items-center gap-2">
        <label class="text-base text-gray-500">Модель:</label>
        <select
          :value="model"
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="store.commit('setModel', $event.target.value)"
        >
          <option v-for="option in models" :key="option.id" :value="option.id">
            {{ modelOptionLabel(option) }}
          </option>
        </select>
      </div>
      <span v-if="usageResetInfo" class="text-base text-gray-500">
        {{ usageResetInfo }}
      </span>
    </div>
    <button
      :disabled="!canRun || loading"
      class="rounded-lg bg-blue-600 px-5 py-2 text-base font-medium text-white transition-all hover:bg-blue-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
      @click="store.dispatch('runCheck')"
    >
      {{ loading ? 'Проверяем...' : 'Запустить проверку' }}
    </button>
  </div>
</template>
