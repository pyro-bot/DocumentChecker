import {
  clearStoredAuthToken,
  getStoredAuthToken,
  storeAuthToken,
} from '../../services/apiClient'
import * as documentCheckerApi from '../../services/documentCheckerApi'

const STARTUP_REQUEST_TIMEOUT_MS = 15000
const STARTUP_RETRY_DELAYS_MS = [1000, 2500, 5000]
const STARTUP_REQUEST_OPTIONS = { timeoutMs: STARTUP_REQUEST_TIMEOUT_MS }

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function isRetriableStartupError(error) {
  if (!error?.status) return true
  return error.status === 408 || error.status === 429 || error.status >= 500
}

async function withStartupRetry(task, onRetry) {
  let lastError = null

  for (let attempt = 1; attempt <= STARTUP_RETRY_DELAYS_MS.length + 1; attempt += 1) {
    try {
      return await task()
    } catch (error) {
      lastError = error
      const canRetry = attempt <= STARTUP_RETRY_DELAYS_MS.length && isRetriableStartupError(error)
      if (!canRetry) break

      onRetry?.(attempt + 1)
      await delay(STARTUP_RETRY_DELAYS_MS[attempt - 1])
    }
  }

  throw lastError
}

export const authStore = {
  state: () => ({
    authToken: getStoredAuthToken(),
    currentUser: null,
    authChecking: Boolean(getStoredAuthToken()),
    authLoadingMessage: 'Проверяем сессию...',
    loginLoading: false,
    loginError: '',
    loginForm: { username: '', password: '' },
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.authToken && state.currentUser),
  },

  mutations: {
    clearAuth(state) {
      state.authToken = ''
      state.currentUser = null
      clearStoredAuthToken()
    },
    setAuthChecking(state, value) {
      state.authChecking = value
    },
    setAuthLoadingMessage(state, value) {
      state.authLoadingMessage = value
    },
    setCurrentUser(state, user) {
      state.currentUser = user
    },
    setAuthToken(state, token) {
      state.authToken = token
      storeAuthToken(token)
    },
    setLoginLoading(state, value) {
      state.loginLoading = value
    },
    setLoginError(state, value) {
      state.loginError = value
    },
    setLoginUsername(state, value) {
      state.loginForm.username = value
    },
    setLoginPassword(state, value) {
      state.loginForm.password = value
    },
  },

  actions: {
    async initialize({ state, commit, dispatch }) {
      if (!state.authToken) {
        commit('setAuthChecking', false)
        return
      }

      try {
        commit('setAuthLoadingMessage', 'Проверяем сессию...')
        const user = await withStartupRetry(
          () => documentCheckerApi.fetchCurrentUser(state.authToken, STARTUP_REQUEST_OPTIONS),
          (attempt) => commit('setAuthLoadingMessage', `Сервер отвечает долго. Повторяем проверку сессии (${attempt}/4)...`),
        )
        commit('setCurrentUser', user)
      } catch {
        commit('clearAuth')
        commit('setAuthChecking', false)
        return
      }

      try {
        await dispatch('loadAppConfig')
      } catch (error) {
        commit('setGlobalError', error.message || 'Не удалось загрузить данные приложения')
      } finally {
        commit('setAuthChecking', false)
      }
    },
    async loadAppConfig({ state, commit, dispatch }) {
      const loadWithRetry = async (label, action, payload = STARTUP_REQUEST_OPTIONS) => {
        commit('setAuthLoadingMessage', `Загружаем ${label}...`)
        await withStartupRetry(
          () => dispatch(action, payload),
          (attempt) => commit('setAuthLoadingMessage', `Не удалось загрузить ${label}. Повторяем попытку (${attempt}/4)...`),
        )
      }

      await loadWithRetry('модели', 'loadModels')
      await loadWithRetry('шаблоны', 'loadTemplates')
      await loadWithRetry('историю проверок', 'loadHistory')

      if (state.currentUser?.role === 'admin') {
        await loadWithRetry('данные администратора', 'loadAdminData')
      }
    },
    async login({ state, commit, dispatch }) {
      commit('setLoginLoading', true)
      commit('setLoginError', '')

      let data = null
      try {
        data = await documentCheckerApi.login({
          username: state.loginForm.username,
          password: state.loginForm.password,
        })
      } catch (error) {
        commit('setLoginError', error.message || 'Не удалось войти')
        commit('setLoginLoading', false)
        return
      }

      commit('setAuthToken', data.access_token)
      commit('setCurrentUser', data.user)
      commit('setLoginPassword', '')
      commit('setAuthChecking', true)

      try {
        await dispatch('loadAppConfig')
      } catch (error) {
        commit('setGlobalError', error.message || 'Не удалось загрузить данные приложения')
      } finally {
        commit('setLoginLoading', false)
        commit('setAuthChecking', false)
      }
    },
    async logout({ state, commit }) {
      try {
        await documentCheckerApi.logout(state.authToken)
      } finally {
        commit('clearAuth')
      }
    },
  },
}
