<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import { TEMPLATE_FILE_ACCEPT, TEMPLATE_FILE_HINT } from '../utils/templates'
import DropZone from './DropZone.vue'
import MultiDropZone from './MultiDropZone.vue'

const store = useStore()
const files = computed(() => store.state.files)
const templates = computed(() => store.state.templates)
const selectedTemplate = computed(() => store.state.selectedTemplate)
const selectedTemplateMeta = computed(() => store.getters.selectedTemplateMeta)
const canPreviewSelectedTemplate = computed(() => store.getters.canPreviewSelectedTemplate)
const currentUser = computed(() => store.state.currentUser)
const templateFileAccept = TEMPLATE_FILE_ACCEPT
const templateFileHint = TEMPLATE_FILE_HINT

function onTemplateChanged(event) {
  store.commit('setSelectedTemplate', event.target.value)
  store.commit('closeTemplatePreview')
}
</script>

<template>
  <div class="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
    <DropZone
      label="Шаблон (эталон)"
      icon="📄"
      :file="files.template"
      :accept="templateFileAccept"
      :file-hint="templateFileHint"
      @file-selected="store.commit('setTemplateFile', $event)"
      @file-removed="store.commit('clearTemplateFile')"
    />

    <MultiDropZone
      label="Документы для проверки"
      icon="📋"
      :files="files.documents"
      @files-added="store.commit('addDocuments', $event)"
      @file-removed="store.commit('removeDocument', $event)"
    />
  </div>

  <div v-if="templates.length" class="mb-5 flex flex-wrap items-center gap-3">
    <label class="text-base text-gray-500">Готовый шаблон:</label>
    <select
      :value="selectedTemplate"
      class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
      @change="onTemplateChanged"
    >
      <option value="">Не выбран</option>
      <option v-for="template in templates" :key="template.id" :value="template.id">
        {{ template.name }}
      </option>
    </select>
    <button
      v-if="canPreviewSelectedTemplate"
      class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 transition-colors hover:bg-gray-50"
      @click="store.dispatch('openTemplatePreview', false)"
    >
      Просмотр
    </button>
    <button
      v-if="currentUser?.role === 'admin' && canPreviewSelectedTemplate"
      class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 transition-colors hover:bg-gray-50"
      @click="store.dispatch('openTemplatePreview', true)"
    >
      Редактировать Markdown
    </button>
    <span v-if="selectedTemplate && selectedTemplateMeta && !canPreviewSelectedTemplate" class="text-base text-gray-400">
      Предпросмотр доступен для .md и .markdown
    </span>
  </div>
</template>
