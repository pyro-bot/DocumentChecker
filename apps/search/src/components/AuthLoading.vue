<script setup>
defineProps({
  message: {
    type: String,
    default: 'Проверяем сессию...',
  },
})
</script>

<template>
  <div class="h-screen overflow-hidden text-gray-900 font-sans bg-[url('/1.jpg')] bg-cover bg-center bg-no-repeat">
    <div class="h-full flex items-center justify-center bg-white/20 backdrop-blur-[2px] px-6">
      <div class="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-6 py-5 shadow-sm">
        <div class="h-1 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full w-2/3 bg-blue-600 rounded-full animate-pulse"></div>
        </div>
        <p class="mt-4 text-base text-gray-600">{{ message }}</p>
      </div>
    </div>
  </div>
</template>
