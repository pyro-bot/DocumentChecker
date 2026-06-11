<script setup>
import CheckResultDetails from './CheckResultDetails.vue'

defineProps({
  fileResults: { type: Array, default: () => [] },
})

defineEmits(['download-report'])
</script>

<template>
  <hr class="my-6 border-gray-100" />
  <h2 class="mb-3 text-base font-semibold">Результаты проверки</h2>

  <div class="flex flex-col gap-3">
    <div
      v-for="fileResult in fileResults"
      :key="fileResult.fileName"
      class="overflow-hidden rounded-xl border border-gray-200 bg-white"
    >
      <button
        class="w-full flex items-center justify-between bg-gray-50 px-5 py-4 text-left text-base font-medium transition-colors hover:bg-gray-100"
        @click="fileResult.open = !fileResult.open"
      >
        <span class="flex items-center gap-3">
          <span v-if="fileResult.loading" class="text-xl animate-spin">⏳</span>
          <span v-else-if="fileResult.error" class="text-xl">❌</span>
          <span v-else-if="fileResult.result && fileResult.result.errors?.length === 0" class="text-xl">✅</span>
          <span v-else class="text-xl">⚠️</span>

          <span class="break-all text-gray-800">{{ fileResult.fileName }}</span>

          <span
            v-if="!fileResult.loading && !fileResult.error && fileResult.result"
            class="rounded-full px-2 py-0.5 text-xs font-normal"
            :class="fileResult.result.errors?.length ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'"
          >
            {{ fileResult.result.errors?.length ? fileResult.result.errors.length + ' ошибок' : 'OK' }}
          </span>

          <span v-if="fileResult.loading" class="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-normal text-gray-400">
            Проверяется...
          </span>
        </span>

        <span class="ml-2 flex-shrink-0 text-lg text-gray-400">{{ fileResult.open ? '▲' : '▼' }}</span>
      </button>

      <div v-if="fileResult.open" class="p-5">
        <CheckResultDetails
          :loading="fileResult.loading"
          :error="fileResult.error"
          :result="fileResult.result"
          :grouped-errors="fileResult.groupedErrors"
          @download="$emit('download-report', fileResult)"
        />
      </div>
    </div>
  </div>
</template>
