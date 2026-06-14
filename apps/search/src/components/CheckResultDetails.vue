<script setup>
import BibliographyResult from './BibliographyResult.vue'
import ErrorGroups from './ErrorGroups.vue'
import MetricsGrid from './MetricsGrid.vue'

defineProps({
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  result: { type: Object, default: null },
  bibliographyLoading: { type: Boolean, default: false },
  bibliographyError: { type: String, default: '' },
  bibliographyResult: { type: Object, default: null },
  groupedErrors: { type: Object, default: () => ({}) },
  showDownload: { type: Boolean, default: true },
})

defineEmits(['download'])
</script>

<template>
  <div v-if="loading" class="text-base text-gray-400">
    Идёт проверка файла...
  </div>

  <div v-else-if="error" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-base text-red-700">
    {{ error }}
  </div>

  <template v-else-if="result">
    <MetricsGrid :result="result" />

    <div
      v-if="result.warnings?.length"
      class="mb-5 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-base text-yellow-800"
    >
      <div v-for="warning in result.warnings" :key="warning">
        {{ warning }}
      </div>
    </div>

    <div
      v-if="!result.errors?.length"
      class="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-base text-green-700"
    >
      Ошибок не найдено — документ полностью соответствует шаблону.
    </div>

    <ErrorGroups v-else :grouped-errors="groupedErrors" />

    <button
      v-if="showDownload"
      class="mt-4 rounded-lg border border-gray-200 bg-white px-4 py-2 text-base text-gray-700 transition-colors hover:bg-gray-50"
      @click="$emit('download')"
    >
      Скачать отчёт (PDF)
    </button>

    <BibliographyResult
      :loading="bibliographyLoading"
      :error="bibliographyError"
      :result="bibliographyResult"
    />
  </template>
</template>
