import {
  clearStoredAuthToken,
  getStoredAuthToken,
  storeAuthToken,
} from '../../services/apiClient'
import * as documentCheckerApi from '../../services/documentCheckerApi'

export const authStore = {
  state: () => ({
    authToken: getStoredAuthToken(),
    currentUser: null,
    authChecking: Boolean(getStoredAuthToken()),
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
        commit('setCurrentUser', await documentCheckerApi.fetchCurrentUser(state.authToken))
        await dispatch('loadAppConfig')
      } catch {
        commit('clearAuth')
      } finally {
        commit('setAuthChecking', false)
      }
    },
    async loadAppConfig({ state, dispatch }) {
      await Promise.all([dispatch('loadModels'), dispatch('loadTemplates'), dispatch('loadHistory')])
      if (state.currentUser?.role === 'admin') {
        await dispatch('loadAdminData')
      }
    },
    async login({ state, commit, dispatch }) {
      commit('setLoginLoading', true)
      commit('setLoginError', '')

      try {
        const data = await documentCheckerApi.login({
          username: state.loginForm.username,
          password: state.loginForm.password,
        })
        commit('setAuthToken', data.access_token)
        commit('setCurrentUser', data.user)
        commit('setLoginPassword', '')
        await dispatch('loadAppConfig')
      } catch (error) {
        commit('setLoginError', error.message || 'Не удалось войти')
      } finally {
        commit('setLoginLoading', false)
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
