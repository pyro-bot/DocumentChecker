<script setup>
const props = defineProps({
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  result: { type: Object, default: null },
})

function statusLabel(status) {
  return {
    confirmed: 'Подтверждено',
    probable: 'Похоже найдено',
    suspicious: 'Сомнительно',
    not_found: 'Не найдено',
    unparsed: 'Не разобрано',
  }[status] || status
}

function statusClass(status) {
  return {
    confirmed: 'bg-green-50 text-green-700 border-green-200',
    probable: 'bg-blue-50 text-blue-700 border-blue-200',
    suspicious: 'bg-orange-50 text-orange-700 border-orange-200',
    not_found: 'bg-red-50 text-red-700 border-red-200',
    unparsed: 'bg-gray-50 text-gray-600 border-gray-200',
  }[status] || 'bg-gray-50 text-gray-600 border-gray-200'
}

function statusCounts() {
  const counts = {
    confirmed: 0,
    probable: 0,
    suspicious: 0,
    not_found: 0,
    unparsed: 0,
  }
  for (const item of props.result?.references || []) {
    counts[item.status] = (counts[item.status] || 0) + 1
  }
  return counts
}

function candidateTitle(candidate) {
  return candidate.title || candidate.url || candidate.source
}

function formatAuthors(authors) {
  if (!authors?.length) return ''
  return authors.slice(0, 3).join(', ') + (authors.length > 3 ? ' et al.' : '')
}
</script>

<template>
  <section class="mt-6 border-t border-gray-100 pt-5">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div>
        <h3 class="text-base font-semibold text-gray-900">Литературные источники</h3>
        <p class="text-sm text-gray-500">Проверка существования записей по бесплатным научным каталогам.</p>
      </div>
      <span
        v-if="result"
        class="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-sm text-gray-600"
      >
        {{ result.checked_count || 0 }} записей
      </span>
    </div>

    <div v-if="loading" class="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-base text-gray-500">
      Проверяем список литературы...
    </div>

    <div v-else-if="error" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-base text-red-700">
      {{ error }}
    </div>

    <template v-else-if="result">
      <div class="mb-4 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-base text-gray-700">
        {{ result.summary }}
      </div>

      <div
        v-if="result.warnings?.length"
        class="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800"
      >
        <div v-for="warning in result.warnings" :key="warning">{{ warning }}</div>
      </div>

      <div class="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <div
          v-for="status in ['confirmed', 'probable', 'suspicious', 'not_found', 'unparsed']"
          :key="status"
          class="rounded-lg border px-3 py-2"
          :class="statusClass(status)"
        >
          <div class="text-xs font-medium">{{ statusLabel(status) }}</div>
          <div class="text-xl font-semibold">{{ statusCounts()[status] || 0 }}</div>
        </div>
      </div>

      <div v-if="!result.references?.length" class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-base text-gray-500">
        Список литературы не найден или не удалось выделить отдельные записи.
      </div>

      <div v-else class="flex flex-col gap-2">
        <details
          v-for="reference in result.references"
          :key="reference.index"
          class="rounded-lg border border-gray-200 bg-white"
        >
          <summary class="cursor-pointer list-none px-4 py-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-sm font-semibold text-gray-500">#{{ reference.index }}</span>
              <span class="rounded-full border px-2 py-0.5 text-xs font-medium" :class="statusClass(reference.status)">
                {{ statusLabel(reference.status) }}
              </span>
              <span class="text-sm text-gray-500">
                confidence {{ Math.round((reference.confidence || 0) * 100) }}%
              </span>
            </div>
            <div class="mt-2 text-base font-medium leading-snug text-gray-800">
              {{ reference.title || reference.raw }}
            </div>
            <div v-if="reference.authors?.length || reference.year" class="mt-1 text-sm text-gray-500">
              {{ formatAuthors(reference.authors) }}<span v-if="reference.year">, {{ reference.year }}</span>
            </div>
          </summary>

          <div class="border-t border-gray-100 px-4 py-3">
            <div class="mb-3 text-sm leading-relaxed text-gray-600">
              {{ reference.reason }}
            </div>
            <div class="mb-3 rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">
              {{ reference.raw }}
            </div>

            <div v-if="reference.candidates?.length" class="flex flex-col gap-2">
              <div class="text-sm font-semibold text-gray-500">Найденные кандидаты</div>
              <a
                v-for="candidate in reference.candidates"
                :key="`${reference.index}-${candidate.source}-${candidate.url}-${candidate.title}`"
                :href="candidate.url || undefined"
                target="_blank"
                rel="noopener noreferrer"
                class="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm transition-colors hover:bg-gray-100"
              >
                <div class="flex flex-wrap items-center gap-2">
                  <span class="font-semibold text-gray-800">{{ candidate.source }}</span>
                  <span class="text-gray-500">{{ Math.round((candidate.confidence || 0) * 100) }}%</span>
                  <span v-if="candidate.year" class="text-gray-500">{{ candidate.year }}</span>
                </div>
                <div class="mt-1 text-gray-700">{{ candidateTitle(candidate) }}</div>
                <div v-if="candidate.authors?.length" class="mt-1 text-gray-500">
                  {{ formatAuthors(candidate.authors) }}
                </div>
              </a>
            </div>
          </div>
        </details>
      </div>
    </template>
  </section>
</template>
