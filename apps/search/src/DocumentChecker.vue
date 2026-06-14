<template>
  <AuthLoading v-if="authChecking" />

  <LoginView v-else-if="!isAuthenticated" />

  <div v-else class="h-screen overflow-hidden text-gray-900 font-sans bg-[url('/1.jpg')] bg-cover bg-center bg-no-repeat">
    <div class="h-full overflow-y-auto bg-white/15 backdrop-blur-[2px]" style="scrollbar-width: none; -ms-overflow-style: none;">
      <div class="max-w-6xl mx-auto px-16 py-10">
        <AppHeader />

        <UploadSection />

        <CheckControls />

        <ProgressBar
          v-if="loading"
          :progress="overallProgress"
          :label="progressLabel"
        />

        <div
          v-if="globalError"
          class="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-base text-red-700"
        >
          {{ globalError }}
        </div>

        <ResultsList v-if="fileResults.length" />

        <HistoryList v-if="historyItems.length" />

        <AdminTabs v-if="currentUser?.role === 'admin'" />

        <p v-if="!fileResults.length && !loading" class="text-base text-gray-400 mt-4">
          Загрузите шаблон и один или несколько документов для запуска проверки.
        </p>
      </div>
    </div>

    <TemplatePreviewModal />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import AdminTabs from './components/AdminTabs.vue'
import AppHeader from './components/AppHeader.vue'
import AuthLoading from './components/AuthLoading.vue'
import CheckControls from './components/CheckControls.vue'
import HistoryList from './components/HistoryList.vue'
import LoginView from './components/LoginView.vue'
import ProgressBar from './components/ProgressBar.vue'
import ResultsList from './components/ResultsList.vue'
import TemplatePreviewModal from './components/TemplatePreviewModal.vue'
import UploadSection from './components/UploadSection.vue'

const store = useStore()

const authChecking = computed(() => store.state.authChecking)
const isAuthenticated = computed(() => store.getters.isAuthenticated)
const currentUser = computed(() => store.state.currentUser)
const loading = computed(() => store.state.loading)
const progressLabel = computed(() => store.state.progressLabel)
const overallProgress = computed(() => store.getters.overallProgress)
const globalError = computed(() => store.state.globalError)
const fileResults = computed(() => store.state.fileResults)
const historyItems = computed(() => store.state.historyItems)

onMounted(() => store.dispatch('initialize'))
</script>
