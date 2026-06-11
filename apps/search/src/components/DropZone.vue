<script setup>
import { ref } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  icon: { type: String, default: '📄' },
  file: { type: Object, default: null },
  accept: { type: String, default: '.docx' },
  fileHint: { type: String, default: '.docx' },
})

const emit = defineEmits(['file-selected', 'file-removed'])
const dragOver = ref(false)
const inputRef = ref(null)

function isTemplateFileName(name) {
  return /\.(docx|md|markdown)$/i.test(name || '')
}

function formatSize(bytes) {
  return bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(1)} КБ`
    : `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}

function onDrop(event) {
  dragOver.value = false
  const file = event.dataTransfer.files[0]
  if (isTemplateFileName(file?.name)) emit('file-selected', file)
}

function onFile(event) {
  const file = event.target.files[0]
  if (isTemplateFileName(file?.name)) emit('file-selected', file)
  event.target.value = ''
}
</script>

<template>
  <div
    class="flex min-h-32 cursor-pointer items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-all duration-150"
    :class="dragOver ? 'border-blue-400 bg-blue-50' : file ? 'border-green-300 bg-green-50' : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'"
    @click="inputRef?.click()"
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="onDrop"
  >
    <input
      ref="inputRef"
      :accept="props.accept"
      class="hidden"
      type="file"
      @change="onFile"
    />

    <div v-if="file" class="flex flex-col items-center gap-1">
      <div class="text-2xl">✅</div>
      <div class="max-w-xs break-all text-base font-medium text-gray-800">{{ file.name }}</div>
      <div class="text-lg text-gray-400">{{ formatSize(file.size) }}</div>
      <button
        class="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-1 text-lg text-red-600 transition-colors hover:bg-red-100"
        @click.stop="$emit('file-removed')"
      >
        Удалить
      </button>
    </div>

    <div v-else class="flex flex-col items-center gap-1">
      <div class="text-2xl">{{ icon }}</div>
      <div class="mt-1 text-base font-medium text-gray-700">{{ label }}</div>
      <div class="mt-0.5 text-lg text-gray-400">{{ fileHint }} - перетащите или нажмите</div>
    </div>
  </div>
</template>
