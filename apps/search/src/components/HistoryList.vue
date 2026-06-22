<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import { formatDate } from '../utils/checkPresentation.js'
import { historyModelLabel, historyTemplateLabel } from '../utils/results'
import CheckResultDetails from './CheckResultDetails.vue'

const store = useStore()
const items = computed(() => store.state.historyItems)
const title = 'История моих проверок'
</script>

<template>
  <hr class="my-6 border-gray-100" />
  <div class="mb-3 flex items-center justify-between gap-3">
    <h2 class="text-base font-semibold">{{ title }}</h2>
    <button
      class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50"
      @click="store.dispatch('loadHistory')"
    >
      Обновить
    </button>
  </div>

  <div
    class="overflow-hidden rounded-xl border border-gray-200 bg-white"
    :class="items.length > 10 ? 'max-h-[720px] overflow-y-auto' : ''"
  >
    <div
      v-for="item in items"
      :key="item.id"
      class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3 last:border-b-0"
    >
      <div class="min-w-0">
        <div class="break-all text-base font-medium text-gray-800">{{ item.document_name }}</div>
        <div class="text-lg text-gray-400">
          {{ formatDate(item.created_at) }} · {{ item.compliance_score }}% · ошибок: {{ item.errors_count }}
        </div>
        <div class="text-base text-gray-500">
          Нейросеть: {{ historyModelLabel(item) }}
        </div>
        <div class="text-base text-gray-500">
          Шаблон: {{ historyTemplateLabel(item) }}
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50"
          @click="store.commit('toggleHistoryItemOpen', item)"
        >
          {{ item.open ? 'Скрыть' : 'Открыть' }}
        </button>
        <button
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50"
          @click="store.dispatch('downloadHistoryReport', item)"
        >
          PDF
        </button>
        <button
          :disabled="!item.source_available"
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50 disabled:opacity-40"
          @click="store.dispatch('downloadHistorySource', item)"
        >
          DOCX
        </button>
        <button
          v-if="item.template_download_available"
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50"
          @click="store.dispatch('downloadHistoryTemplate', item)"
        >
          Шаблон
        </button>
      </div>

      <div v-if="item.open" class="w-full pt-3">
        <CheckResultDetails
          :result="item.result"
          :bibliography-result="item.bibliographyResult"
          :grouped-errors="item.groupedErrors"
          :show-download="false"
        />
      </div>
    </div>
  </div>
</template>
