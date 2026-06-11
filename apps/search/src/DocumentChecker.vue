<template>
  <AuthLoading v-if="authChecking" />

  <LoginView
    v-else-if="!isAuthenticated"
    :login-form="loginForm"
    :login-error="loginError"
    :login-loading="loginLoading"
    @submit="login"
  />

  <div v-else class="h-screen overflow-hidden text-gray-900 font-sans bg-[url('/1.jpg')] bg-cover bg-center bg-no-repeat">
    <div class="h-full overflow-y-auto bg-white/15 backdrop-blur-[2px]" style="scrollbar-width: none; -ms-overflow-style: none;">
      <div class="max-w-6xl mx-auto px-16 py-10">
        <AppHeader :current-user="currentUser" @logout="logout" />

        <UploadSection
          v-model:selected-template="selectedTemplate"
          :files="files"
          :templates="templates"
          :selected-template-meta="selectedTemplateMeta"
          :can-preview-selected-template="canPreviewSelectedTemplate"
          :current-user="currentUser"
          :template-file-accept="TEMPLATE_FILE_ACCEPT"
          :template-file-hint="TEMPLATE_FILE_HINT"
          @template-file-selected="onTemplateFileSelected"
          @template-file-removed="files.template = null"
          @documents-added="onDocumentsAdded"
          @document-removed="removeDocument"
          @template-selected="onSelectedTemplateChanged"
          @preview-template="openTemplatePreview"
        />

        <CheckControls
          v-model:model="model"
          :models="models"
          :can-run="canRun"
          :loading="loading"
          @run="runCheck"
        />

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

        <ResultsList
          v-if="fileResults.length"
          :file-results="fileResults"
          @download-report="downloadReport"
        />

        <HistoryList
          v-if="historyItems.length"
          :items="historyItems"
          title="История моих проверок"
          @refresh="loadHistory"
          @download-report="downloadHistoryReport"
          @download-source="downloadHistorySource"
        />

        <AdminTabs
          v-if="currentUser?.role === 'admin'"
          v-model:checks-user="adminChecksUser"
          v-model:reset-user="adminResetUser"
          :admin-users="adminUsers"
          :admin-checks="adminChecks"
          :reset-loading="adminResetLoading"
          :reset-message="adminResetMessage"
          :admin-template-file="adminTemplateFile"
          :admin-template-upload-loading="adminTemplateUploadLoading"
          :admin-template-upload-message="adminTemplateUploadMessage"
          :template-file-accept="TEMPLATE_FILE_ACCEPT"
          @filter-checks="loadAdminChecks"
          @reset-limits="resetUsageLimits"
          @admin-template-file-selected="onAdminTemplateFileSelected"
          @upload-template="uploadAdminTemplate"
          @download-report="downloadHistoryReport"
          @download-source="downloadHistorySource"
        />

        <p v-if="!fileResults.length && !loading" class="text-base text-gray-400 mt-4">
          Загрузите шаблон и один или несколько документов для запуска проверки.
        </p>
      </div>
    </div>

    <TemplatePreviewModal
      v-model:content="templatePreviewContent"
      v-model:editing="templatePreviewEditing"
      :open="templatePreviewOpen"
      :loading="templatePreviewLoading"
      :saving="templatePreviewSaving"
      :error="templatePreviewError"
      :template="templatePreviewTemplate"
      :selected-template="selectedTemplate"
      :rendered-html="renderedTemplateMarkdown"
      :can-edit="currentUser?.role === 'admin'"
      @close="closeTemplatePreview"
      @save="saveTemplateMarkdown"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
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

const TEMPLATE_FILE_ACCEPT = '.docx,.md,.markdown'
const TEMPLATE_FILE_HINT = '.docx, .md, .markdown'

function isTemplateFileName(name) {
  return /\.(docx|md|markdown)$/i.test(name || '')
}

// ── State ─────────────────────────────────────────────────────────────────────
const API_BASE_URL  = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

const authToken    = ref(localStorage.getItem('auth_token') || '')
const currentUser  = ref(null)
const authChecking = ref(Boolean(authToken.value))
const loginLoading = ref(false)
const loginError   = ref('')
const loginForm    = reactive({ username: '', password: '' })

const files         = reactive({ template: null, documents: [] })
const models        = ref([])
const templates     = ref([])
const selectedTemplate = ref('')
const model         = ref('')
const loading       = ref(false)
const progressLabel = ref('')
const globalError   = ref('')
const fileResults   = ref([])  // Array of { fileName, file, open, loading, error, result, groupedErrors }
const historyItems  = ref([])
const adminUsers    = ref([])
const adminChecks   = ref([])
const adminChecksUser = ref('')
const adminResetUser = ref('')
const adminResetLoading = ref(false)
const adminResetMessage = ref('')
const adminTemplateFile = ref(null)
const adminTemplateUploadLoading = ref(false)
const adminTemplateUploadMessage = ref('')
const templatePreviewOpen = ref(false)
const templatePreviewLoading = ref(false)
const templatePreviewSaving = ref(false)
const templatePreviewEditing = ref(false)
const templatePreviewError = ref('')
const templatePreviewTemplate = ref(null)
const templatePreviewContent = ref('')

// ── File management ───────────────────────────────────────────────────────────
function onDocumentsAdded(newFiles) {
  for (const f of newFiles) {
    // Avoid duplicates by name
    if (!files.documents.find(d => d.name === f.name)) {
      files.documents.push(f)
    }
  }
}

function removeDocument(index) {
  files.documents.splice(index, 1)
}

function onTemplateFileSelected(file) {
  selectedTemplate.value = ''
  files.template = file
}

function onSelectedTemplateChanged() {
  files.template = null
  closeTemplatePreview()
}

function onAdminTemplateFileSelected(file) {
  adminTemplateUploadMessage.value = ''
  adminTemplateFile.value = isTemplateFileName(file?.name) ? file : null
  if (file && !adminTemplateFile.value) {
    adminTemplateUploadMessage.value = 'Можно загрузить только .docx, .md или .markdown'
  }
}


// ── Computed ──────────────────────────────────────────────────────────────────
const isAuthenticated = computed(() => Boolean(authToken.value && currentUser.value))
const hasTemplate = computed(() => Boolean(files.template || selectedTemplate.value))
const canRun = computed(() => hasTemplate.value && files.documents.length > 0 && Boolean(model.value))
const selectedTemplateMeta = computed(() => templates.value.find((item) => item.id === selectedTemplate.value) || null)
const canPreviewSelectedTemplate = computed(() => isMarkdownTemplate(selectedTemplateMeta.value))
const renderedTemplateMarkdown = computed(() => renderMarkdown(templatePreviewContent.value))

const overallProgress = computed(() => {
  if (!fileResults.value.length) return 0
  const done = fileResults.value.filter(fr => !fr.loading).length
  return Math.round((done / fileResults.value.length) * 100)
})

// ── Helpers ───────────────────────────────────────────────────────────────────
function isMarkdownTemplate(template) {
  return template?.kind === 'markdown' || /\.(md|markdown)$/i.test(template?.id || '')
}

function buildGroupedErrors(errors) {
  return reactive({
    structural: { label: 'Структура',      errors: errors.filter(e => e.error_type === 'structural'), open: false },
    formatting: { label: 'Форматирование', errors: errors.filter(e => e.error_type === 'formatting'), open: false },
    content:    { label: 'Содержание',     errors: errors.filter(e => e.error_type === 'content'),    open: false },
    typography: { label: 'Типографика',    errors: errors.filter(e => e.error_type === 'typography'), open: false },
  })
}

function normalizeHistoryItem(item) {
  return {
    ...item,
    open: Boolean(item.open),
    result: item.result || { errors: [], compliance_score: item.compliance_score || 0, summary: '' },
    groupedErrors: buildGroupedErrors(item.result?.errors || []),
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────
function clearAuth() {
  authToken.value = ''
  currentUser.value = null
  localStorage.removeItem('auth_token')
}

function authHeaders() {
  return authToken.value ? { Authorization: `Bearer ${authToken.value}` } : {}
}

function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const apiRoot = API_BASE_URL.endsWith('/api') ? API_BASE_URL : `${API_BASE_URL}/api`
  return `${apiRoot}${normalizedPath}`
}

async function authorizedFetch(url, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeaders() }
  return fetch(url, { ...options, headers })
}

async function loadCurrentUser() {
  if (!authToken.value) {
    authChecking.value = false
    return
  }

  try {
    const res = await authorizedFetch(apiUrl('/auth/me'))
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    currentUser.value = await res.json()
    await loadAppConfig()
  } catch {
    clearAuth()
  } finally {
    authChecking.value = false
  }
}

async function loadAppConfig() {
  await Promise.all([loadModels(), loadTemplates(), loadHistory()])
  if (currentUser.value?.role === 'admin') {
    await loadAdminData()
  }
}

async function loadModels() {
  const res = await authorizedFetch(apiUrl('/models'))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

  models.value = data.models || []
  const hasSelectedModel = models.value.some((item) => item.id === model.value)
  if (!hasSelectedModel) {
    model.value = data.default_model || models.value[0]?.id || ''
  }
}

async function loadTemplates() {
  const res = await authorizedFetch(apiUrl('/templates'))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

  templates.value = data.templates || []
  if (selectedTemplate.value && !templates.value.some((item) => item.id === selectedTemplate.value)) {
    selectedTemplate.value = ''
  }
}

async function openTemplatePreview(editing = false) {
  const template = selectedTemplateMeta.value
  if (!isMarkdownTemplate(template)) return

  templatePreviewOpen.value = true
  templatePreviewEditing.value = Boolean(editing && currentUser.value?.role === 'admin')
  templatePreviewLoading.value = true
  templatePreviewSaving.value = false
  templatePreviewError.value = ''
  templatePreviewTemplate.value = template

  try {
    const res = await authorizedFetch(apiUrl(`/templates/${encodeURIComponent(template.id)}/markdown`))
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    templatePreviewTemplate.value = data
    templatePreviewContent.value = data.content || ''
  } catch (e) {
    templatePreviewError.value = e.message || 'Не удалось открыть шаблон'
    templatePreviewContent.value = ''
  } finally {
    templatePreviewLoading.value = false
  }
}

function closeTemplatePreview() {
  if (templatePreviewSaving.value) return
  templatePreviewOpen.value = false
  templatePreviewLoading.value = false
  templatePreviewEditing.value = false
  templatePreviewError.value = ''
}

async function saveTemplateMarkdown() {
  const templateId = templatePreviewTemplate.value?.id || selectedTemplate.value
  if (!templateId || currentUser.value?.role !== 'admin') return

  templatePreviewSaving.value = true
  templatePreviewError.value = ''

  try {
    const res = await authorizedFetch(apiUrl(`/admin/templates/${encodeURIComponent(templateId)}/markdown`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ content: templatePreviewContent.value }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

    await loadTemplates()
    selectedTemplate.value = data.id
    templatePreviewTemplate.value = data
    templatePreviewEditing.value = false
    adminTemplateUploadMessage.value = `Шаблон сохранён: ${data.name}`
  } catch (e) {
    templatePreviewError.value = e.message || 'Не удалось сохранить шаблон'
  } finally {
    templatePreviewSaving.value = false
  }
}

async function loadHistory() {
  const res = await authorizedFetch(apiUrl('/history'))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  historyItems.value = (data.checks || []).map(normalizeHistoryItem)
}

async function loadAdminData() {
  await Promise.all([loadAdminUsers(), loadAdminChecks()])
}

async function loadAdminUsers() {
  const res = await authorizedFetch(apiUrl('/admin/users'))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  adminUsers.value = data.users || []
}

async function loadAdminChecks(selectedUser = adminChecksUser.value) {
  const userEmail = selectedUser || ''
  if (userEmail !== adminChecksUser.value) {
    adminChecksUser.value = userEmail
  }

  const suffix = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : ''
  const res = await authorizedFetch(apiUrl(`/admin/checks${suffix}`))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  adminChecks.value = (data.checks || []).map(normalizeHistoryItem)
}


async function login() {
  loginLoading.value = true
  loginError.value = ''

  try {
    const res = await fetch(apiUrl('/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        username: loginForm.username,
        password: loginForm.password,
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

    authToken.value = data.access_token
    currentUser.value = data.user
    localStorage.setItem('auth_token', data.access_token)
    loginForm.password = ''
    await loadAppConfig()
  } catch (e) {
    loginError.value = e.message || 'Не удалось войти'
  } finally {
    loginLoading.value = false
  }
}

async function logout() {
  try {
    await authorizedFetch(apiUrl('/auth/logout'), { method: 'POST' })
  } finally {
    clearAuth()
  }
}

async function resetUsageLimits(userEmail = adminResetUser.value) {
  adminResetLoading.value = true
  adminResetMessage.value = ''
  adminResetUser.value = userEmail || ''

  try {
    const payload = {
      user_email: userEmail || null,
      model: null,
    }
    const res = await authorizedFetch(apiUrl('/admin/usage/reset'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    adminResetMessage.value = `Сброшено записей: ${data.reset_records ?? 0}`
    await loadModels()
    await loadAdminUsers().catch(() => {})
  } catch (e) {
    adminResetMessage.value = e.message || 'Не удалось сбросить лимиты'
  } finally {
    adminResetLoading.value = false
  }
}

async function uploadAdminTemplate() {
  if (!adminTemplateFile.value) return

  adminTemplateUploadLoading.value = true
  adminTemplateUploadMessage.value = ''

  try {
    const fd = new FormData()
    fd.append('template_file', adminTemplateFile.value)
    const res = await authorizedFetch(apiUrl('/admin/templates'), { method: 'POST', body: fd })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

    adminTemplateUploadMessage.value = `Шаблон загружен: ${data.name}`
    adminTemplateFile.value = null
    await loadTemplates()
    selectedTemplate.value = data.id
    files.template = null
  } catch (e) {
    adminTemplateUploadMessage.value = e.message || 'Не удалось загрузить шаблон'
  } finally {
    adminTemplateUploadLoading.value = false
  }
}

async function runCheck() {
  loading.value     = true
  globalError.value = ''

  // Init result entries for all documents
  fileResults.value = files.documents.map(f => ({
    fileName:     f.name,
    file:         f,
    open:         false,
    loading:      true,
    error:        null,
    result:       null,
    groupedErrors: buildGroupedErrors([]),
  }))

  progressLabel.value = `Проверяем ${files.documents.length} документов...`

  for (const fr of fileResults.value) {
    await checkSingleFile(fr)
  }

  await loadModels().catch(() => {})
  await loadHistory().catch(() => {})
  if (currentUser.value?.role === 'admin') {
    await loadAdminData().catch(() => {})
  }
  loading.value       = false
  progressLabel.value = 'Готово'
}

async function checkSingleFile(fr) {
  try {
    const fd = new FormData()
    if (selectedTemplate.value) {
      fd.append('template_name', selectedTemplate.value)
    } else {
      fd.append('template_file', files.template)
    }
    fd.append('document_file',  fr.file)
    fd.append('model',     model.value)

    const res = await authorizedFetch(apiUrl('/validate-upload'), { method: 'POST', body: fd })
    if (res.status === 401) {
      clearAuth()
      throw new Error('Сессия истекла')
    }
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    if (data.error) throw new Error(data.error)

    fr.result        = data
    fr.groupedErrors = buildGroupedErrors(data.errors ?? [])
  } catch (e) {
    fr.error = 'Ошибка: ' + e.message
  } finally {
    fr.loading = false
  }
}

async function downloadReport(fr) {
  if (!fr.result) return
  if (fr.result.check_id) {
    await downloadHistoryReport({ id: fr.result.check_id, document_name: fr.fileName })
    return
  }
  const report = {
    template:           selectedTemplate.value || files.template?.name,
    document:           fr.fileName,
    model:              model.value,
    result:             fr.result,
    timestamp:          new Date().toISOString(),
    checked_formatting: true,
  }
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const a = Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(blob),
    download: `report_${fr.fileName.replace('.docx', '')}_${Date.now()}.json`,
  })
  a.click()
  URL.revokeObjectURL(a.href)
}

async function downloadHistoryReport(item) {
  try {
    await downloadBlob(
      apiUrl(`/history/${item.id}/report.pdf`),
      `report_${(item.document_name || 'document').replace(/\.docx$/i, '')}.pdf`,
    )
  } catch (e) {
    globalError.value = e.message || 'Не удалось скачать отчет'
  }
}

async function downloadHistorySource(item) {
  try {
    await downloadBlob(
      apiUrl(`/history/${item.id}/source`),
      item.document_name || 'document.docx',
    )
  } catch (e) {
    globalError.value = e.message || 'Не удалось скачать исходный файл'
  }
}

async function downloadBlob(url, fallbackName) {
  const res = await authorizedFetch(url)
  const blob = await res.blob()
  if (!res.ok) {
    const message = await blob.text().catch(() => '')
    throw new Error(message || `HTTP ${res.status}`)
  }
  const disposition = res.headers.get('content-disposition') || ''
  const filename = parseDownloadFilename(disposition) || fallbackName
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(blob),
    download: filename,
  })
  a.click()
  URL.revokeObjectURL(a.href)
}

function parseDownloadFilename(disposition) {
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utfMatch) return decodeURIComponent(utfMatch[1])
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] || ''
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function sanitizeMarkdownUrl(value) {
  const trimmed = String(value || '').trim()
  if (/^(https?:\/\/|mailto:|#)/i.test(trimmed)) return escapeHtml(trimmed)
  return ''
}

function renderInlineMarkdown(value) {
  const placeholders = []
  const stash = (html) => {
    const key = `%%MDPH${placeholders.length}%%`
    placeholders.push([key, html])
    return key
  }

  let text = String(value ?? '')
    .replace(/`([^`]+)`/g, (_, code) => stash(`<code>${escapeHtml(code)}</code>`))
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, label, href) => {
      const safeHref = sanitizeMarkdownUrl(href)
      if (!safeHref) return match
      return stash(`<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`)
    })

  text = escapeHtml(text)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/_([^_]+)_/g, '<em>$1</em>')

  for (const [key, html] of placeholders) {
    text = text.replaceAll(key, html)
  }
  return text
}

function renderMarkdownTable(lines) {
  const cells = (line) => line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim())
  const headers = cells(lines[0])
  const rows = lines.slice(2).map(cells)
  return [
    '<table>',
    '<thead><tr>',
    headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join(''),
    '</tr></thead>',
    '<tbody>',
    rows.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join('')}</tr>`).join(''),
    '</tbody></table>',
  ].join('')
}

function renderMarkdown(markdown) {
  const lines = String(markdown ?? '').replace(/\r\n/g, '\n').split('\n')
  const html = []
  let paragraph = []
  let listType = null
  let listItems = []
  let quoteLines = []
  let codeLines = []
  let inCode = false

  const flushParagraph = () => {
    if (!paragraph.length) return
    html.push(`<p>${renderInlineMarkdown(paragraph.join(' '))}</p>`)
    paragraph = []
  }
  const flushList = () => {
    if (!listType) return
    html.push(`<${listType}>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</${listType}>`)
    listType = null
    listItems = []
  }
  const flushQuote = () => {
    if (!quoteLines.length) return
    html.push(`<blockquote>${quoteLines.map((line) => `<p>${renderInlineMarkdown(line)}</p>`).join('')}</blockquote>`)
    quoteLines = []
  }
  const flushCode = () => {
    html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
    codeLines = []
  }

  for (let i = 0; i < lines.length; i += 1) {
    const raw = lines[i]
    const trimmed = raw.trim()

    if (trimmed.startsWith('```')) {
      if (inCode) {
        flushCode()
        inCode = false
      } else {
        flushParagraph()
        flushList()
        flushQuote()
        inCode = true
      }
      continue
    }

    if (inCode) {
      codeLines.push(raw)
      continue
    }

    const next = lines[i + 1]?.trim() || ''
    if (trimmed.includes('|') && /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(next)) {
      flushParagraph()
      flushList()
      flushQuote()
      const tableLines = [trimmed, next]
      i += 2
      while (i < lines.length && lines[i].trim().includes('|')) {
        tableLines.push(lines[i].trim())
        i += 1
      }
      i -= 1
      html.push(renderMarkdownTable(tableLines))
      continue
    }

    if (!trimmed) {
      flushParagraph()
      flushList()
      flushQuote()
      continue
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      flushParagraph()
      flushList()
      flushQuote()
      const level = heading[1].length
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`)
      continue
    }

    if (/^---+$/.test(trimmed)) {
      flushParagraph()
      flushList()
      flushQuote()
      html.push('<hr />')
      continue
    }

    const quote = trimmed.match(/^>\s?(.*)$/)
    if (quote) {
      flushParagraph()
      flushList()
      quoteLines.push(quote[1])
      continue
    }

    const unordered = trimmed.match(/^[-*+]\s+(.+)$/)
    const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/)
    if (unordered || ordered) {
      flushParagraph()
      flushQuote()
      const currentType = unordered ? 'ul' : 'ol'
      if (listType && listType !== currentType) flushList()
      listType = currentType
      listItems.push((unordered || ordered)[1])
      continue
    }

    flushList()
    flushQuote()
    paragraph.push(trimmed)
  }

  if (inCode) flushCode()
  flushParagraph()
  flushList()
  flushQuote()

  return html.join('\n') || '<p class="text-gray-400">Шаблон пуст.</p>'
}

onMounted(loadCurrentUser)
</script>
