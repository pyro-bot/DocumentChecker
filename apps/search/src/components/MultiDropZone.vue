<script setup>
import { ref } from 'vue'

defineProps({
  label: { type: String, required: true },
  icon: { type: String, default: '📋' },
  files: { type: Array, default: () => [] },
})

const emit = defineEmits(['files-added', 'file-removed'])
const dragOver = ref(false)
const inputRef = ref(null)

function formatSize(bytes) {
  return bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(1)} КБ`
    : `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}

function filterDocx(fileList) {
  return Array.from(fileList || []).filter((file) => /\.docx$/i.test(file.name))
}

function onDrop(event) {
  dragOver.value = false
  const newFiles = filterDocx(event.dataTransfer.files)
  if (newFiles.length) emit('files-added', newFiles)
}

function onFile(event) {
  const newFiles = filterDocx(event.target.files)
  if (newFiles.length) emit('files-added', newFiles)
  event.target.value = ''
}
</script>

<template>
  <div
    class="rounded-xl border-2 border-dashed transition-all duration-150"
    :class="dragOver ? 'border-blue-400 bg-blue-50' : files.length ? 'border-green-300 bg-green-50' : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'"
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="onDrop"
  >
    <div
      class="flex min-h-24 cursor-pointer flex-col items-center justify-center p-4 text-center"
      @click="inputRef?.click()"
    >
      <input
        ref="inputRef"
        accept=".docx"
        class="hidden"
        multiple
        type="file"
        @change="onFile"
      />
      <div class="text-2xl">{{ files.length ? '➕' : icon }}</div>
      <div class="mt-1 text-base font-medium text-gray-700">
        {{ files.length ? 'Добавить ещё файлы' : label }}
      </div>
      <div class="mt-0.5 text-lg text-gray-400">.docx - перетащите или нажмите</div>
    </div>

    <div v-if="files.length" class="flex flex-col gap-2 border-t border-gray-200 px-4 pb-3">
      <div
        v-for="(file, index) in files"
        :key="file.name + index"
        class="flex items-center justify-between gap-2 pt-2"
      >
        <div class="flex min-w-0 items-center gap-2">
          <span class="text-base">📋</span>
          <div class="min-w-0">
            <div class="truncate text-base text-gray-800">{{ file.name }}</div>
            <div class="text-lg text-gray-400">{{ formatSize(file.size) }}</div>
          </div>
        </div>
        <button
          class="flex-shrink-0 rounded-md border border-red-200 bg-red-50 px-2.5 py-1 text-lg text-red-600 transition-colors hover:bg-red-100"
          @click.stop="$emit('file-removed', index)"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>
