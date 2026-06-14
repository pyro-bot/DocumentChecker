const AUTH_TOKEN_KEY = 'auth_token'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export function getStoredAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function storeAuthToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearStoredAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY)
}

export function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const apiRoot = API_BASE_URL.endsWith('/api') ? API_BASE_URL : `${API_BASE_URL}/api`
  return `${apiRoot}${normalizedPath}`
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function apiFetch(path, options = {}) {
  const { token, headers: requestHeaders = {}, ...fetchOptions } = options
  const headers = { ...requestHeaders, ...authHeaders(token) }
  return fetch(apiUrl(path), { ...fetchOptions, headers })
}

export async function requestJson(path, options = {}) {
  const response = await apiFetch(path, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(data.detail || `HTTP ${response.status}`, response.status, data)
  }
  return data
}

export async function requestBlob(path, options = {}) {
  const { fallbackName = '', ...requestOptions } = options
  const response = await apiFetch(path, requestOptions)
  const blob = await response.blob()
  if (!response.ok) {
    const message = await blob.text().catch(() => '')
    throw new ApiError(message || `HTTP ${response.status}`, response.status)
  }

  const disposition = response.headers.get('content-disposition') || ''
  return {
    blob,
    filename: parseDownloadFilename(disposition) || fallbackName,
  }
}

function parseDownloadFilename(disposition) {
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utfMatch) return decodeURIComponent(utfMatch[1])
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] || ''
}
