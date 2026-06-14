<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const loginForm = computed(() => store.state.loginForm)
const loginError = computed(() => store.state.loginError)
const loginLoading = computed(() => store.state.loginLoading)

const username = computed({
  get: () => store.state.loginForm.username,
  set: (value) => store.commit('setLoginUsername', value),
})

const password = computed({
  get: () => store.state.loginForm.password,
  set: (value) => store.commit('setLoginPassword', value),
})

function submit() {
  store.dispatch('login')
}
</script>

<template>
  <div class="h-screen overflow-hidden text-gray-900 font-sans bg-[url('/1.jpg')] bg-cover bg-center bg-no-repeat">
    <div class="h-full flex items-center justify-center bg-white/20 backdrop-blur-[2px] px-6">
      <form
        class="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-6 py-6 shadow-sm"
        @submit.prevent="submit"
      >
        <h1 class="text-2xl font-semibold tracking-tight">Вход</h1>
        <div class="mt-5 flex flex-col gap-4">
          <label class="flex flex-col gap-1 text-base font-medium text-gray-700">
            Логин
            <input
              v-model.trim="username"
              autocomplete="username"
              class="rounded-lg border border-gray-200 px-3 py-2 text-base font-normal text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              type="text"
              required
            />
          </label>
          <label class="flex flex-col gap-1 text-base font-medium text-gray-700">
            Пароль
            <input
              v-model="password"
              autocomplete="current-password"
              class="rounded-lg border border-gray-200 px-3 py-2 text-base font-normal text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              type="password"
              required
            />
          </label>
        </div>
        <div
          v-if="loginError"
          class="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-base text-red-700"
        >
          {{ loginError }}
        </div>
        <button
          :disabled="loginLoading || !loginForm.username || !loginForm.password"
          class="mt-5 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-base font-medium text-white transition-all hover:bg-blue-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
          type="submit"
        >
          {{ loginLoading ? 'Входим...' : 'Войти' }}
        </button>
      </form>
    </div>
  </div>
</template>
