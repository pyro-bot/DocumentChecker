<script setup>
defineProps({
  open: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  editing: { type: Boolean, default: false },
  error: { type: String, default: '' },
  template: { type: Object, default: null },
  selectedTemplate: { type: String, default: '' },
  content: { type: String, default: '' },
  renderedHtml: { type: String, default: '' },
  canEdit: { type: Boolean, default: false },
})

defineEmits(['close', 'update:editing', 'update:content', 'save'])
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/45 px-4 py-6"
    @click.self="$emit('close')"
  >
    <div class="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl">
      <div class="flex items-center justify-between gap-3 border-b border-gray-200 px-5 py-4">
        <div class="min-w-0">
          <h2 class="truncate text-lg font-semibold text-gray-900">
            {{ editing ? 'Редактирование шаблона' : 'Просмотр шаблона' }}
          </h2>
          <div class="truncate text-base text-gray-500">{{ template?.name || selectedTemplate }}</div>
        </div>
        <button
          class="flex-shrink-0 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base text-gray-700 hover:bg-gray-50"
          @click="$emit('close')"
        >
          Закрыть
        </button>
      </div>

      <div class="min-h-0 flex-1 overflow-auto px-5 py-4">
        <div v-if="loading" class="text-base text-gray-500">Загружаем шаблон...</div>
        <div
          v-else-if="error"
          class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-base text-red-700"
        >
          {{ error }}
        </div>
        <textarea
          v-else-if="editing"
          :value="content"
          class="h-[60vh] w-full resize-none rounded-lg border border-gray-200 bg-white px-4 py-3 font-mono text-base leading-relaxed text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          spellcheck="false"
          @input="$emit('update:content', $event.target.value)"
        ></textarea>
        <div
          v-else
          class="markdown-preview max-w-none text-base leading-relaxed text-gray-800"
          v-html="renderedHtml"
        ></div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 px-5 py-4">
        <div class="text-base text-gray-500">
          {{ editing ? 'Изменения сохраняются в выбранный Markdown-файл.' : 'Markdown отрендерен в браузере.' }}
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-if="canEdit && !editing && !loading && !error"
            class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 hover:bg-gray-50"
            @click="$emit('update:editing', true)"
          >
            Редактировать
          </button>
          <button
            v-if="editing"
            class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 hover:bg-gray-50"
            @click="$emit('update:editing', false)"
          >
            Показать предпросмотр
          </button>
          <button
            v-if="editing"
            :disabled="saving"
            class="rounded-lg bg-blue-600 px-4 py-2 text-base font-medium text-white hover:bg-blue-700 disabled:opacity-40"
            @click="$emit('save')"
          >
            {{ saving ? 'Сохраняем...' : 'Сохранить' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.markdown-preview :deep(h1),
.markdown-preview :deep(h2),
.markdown-preview :deep(h3),
.markdown-preview :deep(h4),
.markdown-preview :deep(h5),
.markdown-preview :deep(h6) {
  margin: 1.1rem 0 0.5rem;
  font-weight: 700;
  line-height: 1.25;
  color: #111827;
}

.markdown-preview :deep(h1) { font-size: 1.5rem; }
.markdown-preview :deep(h2) { font-size: 1.25rem; }
.markdown-preview :deep(h3) { font-size: 1.125rem; }
.markdown-preview :deep(p),
.markdown-preview :deep(ul),
.markdown-preview :deep(ol),
.markdown-preview :deep(blockquote),
.markdown-preview :deep(pre),
.markdown-preview :deep(table) {
  margin: 0.75rem 0;
}

.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  padding-left: 1.5rem;
}

.markdown-preview :deep(ul) { list-style: disc; }
.markdown-preview :deep(ol) { list-style: decimal; }
.markdown-preview :deep(blockquote) {
  border-left: 4px solid #d1d5db;
  color: #4b5563;
  padding-left: 1rem;
}

.markdown-preview :deep(code) {
  border-radius: 0.375rem;
  background: #f3f4f6;
  padding: 0.1rem 0.35rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.markdown-preview :deep(pre) {
  overflow: auto;
  border-radius: 0.5rem;
  background: #111827;
  color: #f9fafb;
  padding: 1rem;
}

.markdown-preview :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}

.markdown-preview :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}

.markdown-preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.markdown-preview :deep(th),
.markdown-preview :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 0.5rem 0.75rem;
  text-align: left;
  vertical-align: top;
}

.markdown-preview :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}
</style>
