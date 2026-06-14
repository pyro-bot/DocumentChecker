import { requestBlob, requestJson } from './apiClient'

const jsonHeaders = { 'Content-Type': 'application/json', Accept: 'application/json' }

export function login(credentials) {
  return requestJson('/auth/login', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(credentials),
  })
}

export function logout(token) {
  return requestJson('/auth/logout', { token, method: 'POST' })
}

export function fetchCurrentUser(token) {
  return requestJson('/auth/me', { token })
}

export function fetchModels(token) {
  return requestJson('/models', { token })
}

export function fetchTemplates(token) {
  return requestJson('/templates', { token })
}

export function fetchTemplateMarkdown(token, templateId) {
  return requestJson(`/templates/${encodeURIComponent(templateId)}/markdown`, { token })
}

export function saveTemplateMarkdown(token, templateId, content) {
  return requestJson(`/admin/templates/${encodeURIComponent(templateId)}/markdown`, {
    token,
    method: 'PUT',
    headers: jsonHeaders,
    body: JSON.stringify({ content }),
  })
}

export function fetchHistory(token) {
  return requestJson('/history', { token })
}

export function fetchAdminUsers(token) {
  return requestJson('/admin/users', { token })
}

export function fetchAdminChecks(token, userEmail = '') {
  const suffix = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : ''
  return requestJson(`/admin/checks${suffix}`, { token })
}

export function resetUsageLimits(token, { userEmail = null, model = null } = {}) {
  return requestJson('/admin/usage/reset', {
    token,
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ user_email: userEmail, model }),
  })
}

export function setUsageLimit(token, payload) {
  return requestJson('/admin/usage/limit', {
    token,
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  })
}

export function uploadAdminTemplate(token, templateFile) {
  const formData = new FormData()
  formData.append('template_file', templateFile)
  return requestJson('/admin/templates', {
    token,
    method: 'POST',
    body: formData,
  })
}

export function validateUpload(token, { selectedTemplate, templateFile, documentFile, model }) {
  const formData = new FormData()
  if (selectedTemplate) {
    formData.append('template_name', selectedTemplate)
  } else {
    formData.append('template_file', templateFile)
  }
  formData.append('document_file', documentFile)
  formData.append('model', model)

  return requestJson('/validate-upload', {
    token,
    method: 'POST',
    body: formData,
  })
}

export function checkBibliographyUpload(token, documentFile, maxReferences = 30) {
  const formData = new FormData()
  formData.append('document_file', documentFile)
  formData.append('max_references', String(maxReferences))

  return requestJson('/bibliography/check-upload', {
    token,
    method: 'POST',
    body: formData,
  })
}

export function downloadHistoryReport(token, item) {
  return requestBlob(`/history/${item.id}/report.pdf`, {
    token,
    fallbackName: `report_${(item.document_name || 'document').replace(/\.docx$/i, '')}.pdf`,
  })
}

export function downloadHistorySource(token, item) {
  return requestBlob(`/history/${item.id}/source`, {
    token,
    fallbackName: item.document_name || 'document.docx',
  })
}
