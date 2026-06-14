<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const currentUser = computed(() => store.state.currentUser)
</script>

<template>
  <div class="mb-8">
    <h1 class="text-2xl font-semibold tracking-tight">Проверка документов</h1>
    <p class="text-base text-gray-500 mt-1">
      Загрузите шаблон и документы для проверки структуры, содержания и форматирования
    </p>
    <div class="mt-3 flex flex-wrap items-center gap-3 text-base text-gray-600">
      <span class="rounded-lg border border-gray-200 bg-white px-3 py-1.5">{{ currentUser?.email }}</span>
      <button
        class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-gray-700 transition-colors hover:bg-gray-50"
        @click="store.dispatch('logout')"
      >
        Выйти
      </button>
    </div>
  </div>
</template>
