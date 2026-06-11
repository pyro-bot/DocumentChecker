<script setup>
import { computed, ref, watch } from 'vue'
import { formatDate } from '../utils/checkPresentation.js'
import CheckResultDetails from './CheckResultDetails.vue'

const props = defineProps({
  adminUsers: { type: Array, default: () => [] },
  adminChecks: { type: Array, default: () => [] },
  checksUser: { type: String, default: '' },
  resetUser: { type: String, default: '' },
  resetLoading: { type: Boolean, default: false },
  resetMessage: { type: String, default: '' },
  adminTemplateFile: { type: Object, default: null },
  adminTemplateUploadLoading: { type: Boolean, default: false },
  adminTemplateUploadMessage: { type: String, default: '' },
  templateFileAccept: { type: String, default: '.docx,.md,.markdown' },
})

const emit = defineEmits([
  'update:checksUser',
  'update:resetUser',
  'filter-checks',
  'reset-limits',
  'admin-template-file-selected',
  'upload-template',
  'download-report',
  'download-source',
])

const activeTab = ref('checks')
const adminTemplateInput = ref(null)
const userSearch = ref('')
const checksUserQuery = ref(props.checksUser)

const tabs = [
  { id: 'checks', label: 'Работы' },
  { id: 'users', label: 'Пользователи' },
  { id: 'tools', label: 'Шаблоны и лимиты' },
]

watch(
  () => props.adminTemplateFile,
  (file) => {
    if (!file && adminTemplateInput.value) adminTemplateInput.value.value = ''
  },
)

watch(
  () => props.checksUser,
  (email) => {
    checksUserQuery.value = email
  },
)

const filteredAdminUsers = computed(() => {
  const query = userSearch.value.trim().toLowerCase()
  if (!query) return props.adminUsers

  return props.adminUsers.filter((user) =>
    [user.email, user.role]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query)),
  )
})

function resolveUserEmail(value) {
  const query = value.trim()
  if (!query) return ''

  const exactMatch = props.adminUsers.find((user) => user.email === query)
  if (exactMatch) return exactMatch.email

  const partialMatches = props.adminUsers.filter((user) =>
    user.email.toLowerCase().includes(query.toLowerCase()),
  )
  return partialMatches.length === 1 ? partialMatches[0].email : query
}

function onChecksUserChanged() {
  const email = resolveUserEmail(checksUserQuery.value)
  checksUserQuery.value = email
  emit('update:checksUser', email)
  emit('filter-checks', email)
}

function clearChecksUser() {
  checksUserQuery.value = ''
  emit('update:checksUser', '')
  emit('filter-checks', '')
}

function onAdminTemplateSelected(event) {
  emit('admin-template-file-selected', event.target.files?.[0] || null)
}

function resetUserLimits(email) {
  emit('update:resetUser', email)
  emit('reset-limits', email)
}
</script>

<template>
  <hr class="my-6 border-gray-100" />

  <section class="mb-5">
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="rounded-lg border px-4 py-2 text-base font-medium transition-colors"
        :class="activeTab === tab.id ? 'border-blue-600 bg-blue-600 text-white' : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
        <span v-if="tab.id === 'checks'" class="ml-1 opacity-80">{{ adminChecks.length }}</span>
        <span v-if="tab.id === 'users'" class="ml-1 opacity-80">{{ adminUsers.length }}</span>
      </button>
    </div>

    <div v-if="activeTab === 'checks'">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-base font-semibold">Проверки пользователей</h2>
        <div class="flex flex-wrap items-center gap-2">
          <input
            v-model.trim="checksUserQuery"
            list="admin-checks-users"
            placeholder="Все пользователи"
            class="min-w-64 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
            @change="onChecksUserChanged"
            @keyup.enter="onChecksUserChanged"
          />
          <datalist id="admin-checks-users">
            <option v-for="user in adminUsers" :key="user.email" :value="user.email">
              {{ user.email }}
            </option>
          </datalist>
          <button
            type="button"
            class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50"
            @click="clearChecksUser"
          >
            Все
          </button>
        </div>
      </div>

      <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div
          v-for="item in adminChecks"
          :key="item.id"
          class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3 last:border-b-0"
        >
          <div class="min-w-0">
            <div class="break-all text-base font-medium text-gray-800">{{ item.document_name }}</div>
            <div class="text-lg text-gray-400">
              {{ item.user_email }} · {{ formatDate(item.created_at) }} · {{ item.compliance_score }}% · ошибок: {{ item.errors_count }}
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50"
              @click="item.open = !item.open"
            >
              {{ item.open ? 'Скрыть' : 'Открыть' }}
            </button>
            <button
              class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50"
              @click="$emit('download-report', item)"
            >
              PDF
            </button>
            <button
              :disabled="!item.source_available"
              class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base hover:bg-gray-50 disabled:opacity-40"
              @click="$emit('download-source', item)"
            >
              DOCX
            </button>
          </div>

          <div v-if="item.open" class="w-full pt-3">
            <CheckResultDetails
              :result="item.result"
              :grouped-errors="item.groupedErrors"
              :show-download="false"
            />
          </div>
        </div>
        <div v-if="!adminChecks.length" class="px-4 py-3 text-base text-gray-400">
          Проверок пока нет.
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'users'">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-base font-semibold">Пользователи</h2>
        <input
          v-model.trim="userSearch"
          type="search"
          placeholder="Поиск по имени пользователя"
          class="min-w-64 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div
          v-for="user in filteredAdminUsers"
          :key="user.email"
          class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3 last:border-b-0"
        >
          <div class="min-w-0">
            <div class="break-all text-base font-medium text-gray-800">{{ user.email }}</div>
            <div class="text-lg text-gray-400">
              {{ user.role }} · вход: {{ formatDate(user.last_login_at) }}
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <div class="text-base text-gray-600">
              Проверок: {{ user.check_count || 0 }}
            </div>
            <button
              type="button"
              :disabled="resetLoading"
              class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              @click="resetUserLimits(user.email)"
            >
              {{ resetLoading && resetUser === user.email ? 'Сбрасываем...' : 'Сбросить лимиты' }}
            </button>
          </div>
        </div>
        <div v-if="!filteredAdminUsers.length" class="px-4 py-3 text-base text-gray-400">
          {{ adminUsers.length ? 'Пользователи не найдены.' : 'Пользователей пока нет.' }}
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col gap-4">
      <div class="flex flex-wrap items-center gap-3">
        <input
          ref="adminTemplateInput"
          :accept="templateFileAccept"
          class="hidden"
          type="file"
          @change="onAdminTemplateSelected"
        />
        <button
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 transition-colors hover:bg-gray-50"
          @click="adminTemplateInput?.click()"
        >
          {{ adminTemplateFile ? adminTemplateFile.name : 'Выбрать шаблон' }}
        </button>
        <button
          :disabled="!adminTemplateFile || adminTemplateUploadLoading"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-40"
          @click="$emit('upload-template')"
        >
          {{ adminTemplateUploadLoading ? 'Загружаем...' : 'Загрузить шаблон' }}
        </button>
        <span v-if="adminTemplateUploadMessage" class="text-base text-gray-600">{{ adminTemplateUploadMessage }}</span>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <label class="text-base text-gray-500">Пользователь:</label>
        <select
          :value="resetUser"
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="$emit('update:resetUser', $event.target.value)"
        >
          <option value="">Все пользователи</option>
          <option v-for="user in adminUsers" :key="user.email" :value="user.email">
            {{ user.email }} · {{ user.check_count || 0 }} проверок
          </option>
        </select>
        <button
          :disabled="resetLoading"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-base font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-40"
          @click="$emit('reset-limits')"
        >
          {{ resetLoading ? 'Сбрасываем...' : 'Сбросить лимиты' }}
        </button>
        <span v-if="resetMessage" class="text-base text-gray-600">{{ resetMessage }}</span>
      </div>
    </div>
  </section>
</template>
