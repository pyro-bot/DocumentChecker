<script setup>
import DropZone from './DropZone.vue'
import MultiDropZone from './MultiDropZone.vue'

defineProps({
  files: { type: Object, required: true },
  templates: { type: Array, default: () => [] },
  selectedTemplate: { type: String, default: '' },
  selectedTemplateMeta: { type: Object, default: null },
  canPreviewSelectedTemplate: { type: Boolean, default: false },
  currentUser: { type: Object, default: null },
  templateFileAccept: { type: String, default: '.docx,.md,.markdown' },
  templateFileHint: { type: String, default: '.docx, .md, .markdown' },
})

const emit = defineEmits([
  'template-file-selected',
  'template-file-removed',
  'documents-added',
  'document-removed',
  'update:selectedTemplate',
  'template-selected',
  'preview-template',
])

function onTemplateChanged(event) {
  emit('update:selectedTemplate', event.target.value)
  emit('template-selected')
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
      @file-selected="$emit('template-file-selected', $event)"
      @file-removed="$emit('template-file-removed')"
    />

    <MultiDropZone
      label="Документы для проверки"
      icon="📋"
      :files="files.documents"
      @files-added="$emit('documents-added', $event)"
      @file-removed="$emit('document-removed', $event)"
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
      @click="$emit('preview-template', false)"
    >
      Просмотр
    </button>
    <button
      v-if="currentUser?.role === 'admin' && canPreviewSelectedTemplate"
      class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 transition-colors hover:bg-gray-50"
      @click="$emit('preview-template', true)"
    >
      Редактировать Markdown
    </button>
    <span v-if="selectedTemplate && selectedTemplateMeta && !canPreviewSelectedTemplate" class="text-base text-gray-400">
      Предпросмотр доступен для .md и .markdown
    </span>
  </div>
</template>
