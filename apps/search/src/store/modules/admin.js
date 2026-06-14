import * as documentCheckerApi from '../../services/documentCheckerApi'
import { normalizeHistoryItem } from '../../utils/results'
import { isTemplateFileName } from '../../utils/templates'

export const adminStore = {
  state: () => ({
    adminUsers: [],
    adminChecks: [],
    adminChecksUser: '',
    adminResetUser: '',
    adminResetLoading: false,
    adminResetMessage: '',
    adminQuotaUser: '',
    adminQuotaModel: '',
    adminQuotaAvailable: '',
    adminQuotaLoading: false,
    adminQuotaMessage: '',
    adminTemplateFile: null,
    adminTemplateUploadLoading: false,
    adminTemplateUploadMessage: '',
  }),

  mutations: {
    setAdminUsers(state, users) {
      state.adminUsers = users || []
    },
    setAdminChecks(state, checks) {
      state.adminChecks = (checks || []).map(normalizeHistoryItem)
    },
    setAdminChecksUser(state, email) {
      state.adminChecksUser = email || ''
    },
    setAdminResetUser(state, email) {
      state.adminResetUser = email || ''
    },
    setAdminResetLoading(state, value) {
      state.adminResetLoading = value
    },
    setAdminResetMessage(state, value) {
      state.adminResetMessage = value
    },
    setAdminQuotaUser(state, value) {
      state.adminQuotaUser = value
    },
    setAdminQuotaModel(state, value) {
      state.adminQuotaModel = value
    },
    setAdminQuotaAvailable(state, value) {
      state.adminQuotaAvailable = value
    },
    setAdminQuotaLoading(state, value) {
      state.adminQuotaLoading = value
    },
    setAdminQuotaMessage(state, value) {
      state.adminQuotaMessage = value
    },
    setAdminTemplateFile(state, file) {
      if (file) {
        state.adminTemplateUploadMessage = ''
      }
      state.adminTemplateFile = isTemplateFileName(file?.name) ? file : null
      if (file && !state.adminTemplateFile) {
        state.adminTemplateUploadMessage = 'Можно загрузить только .docx, .md или .markdown'
      }
    },
    setAdminTemplateUploadLoading(state, value) {
      state.adminTemplateUploadLoading = value
    },
    setAdminTemplateUploadMessage(state, value) {
      state.adminTemplateUploadMessage = value
    },
  },

  actions: {
    async loadAdminData({ dispatch }) {
      await Promise.all([dispatch('loadAdminUsers'), dispatch('loadAdminChecks')])
    },
    async loadAdminUsers({ state, commit }) {
      const data = await documentCheckerApi.fetchAdminUsers(state.authToken)
      commit('setAdminUsers', data.users || [])
    },
    async loadAdminChecks({ state, commit }, selectedUser = state.adminChecksUser) {
      const userEmail = selectedUser || ''
      commit('setAdminChecksUser', userEmail)
      const data = await documentCheckerApi.fetchAdminChecks(state.authToken, userEmail)
      commit('setAdminChecks', data.checks || [])
    },
    async resetUsageLimits({ state, commit, dispatch }, userEmail = state.adminResetUser) {
      commit('setAdminResetLoading', true)
      commit('setAdminResetMessage', '')
      commit('setAdminResetUser', userEmail || '')

      try {
        const data = await documentCheckerApi.resetUsageLimits(state.authToken, {
          userEmail: userEmail || null,
          model: null,
        })
        commit('setAdminResetMessage', `Сброшено записей: ${data.reset_records ?? 0}`)
        await dispatch('loadModels')
        await dispatch('loadAdminUsers').catch(() => {})
      } catch (error) {
        commit('setAdminResetMessage', error.message || 'Не удалось сбросить лимиты')
      } finally {
        commit('setAdminResetLoading', false)
      }
    },
    async setUserUsageLimit({ state, commit, dispatch }) {
      const availableChecks = Number(state.adminQuotaAvailable)
      commit('setAdminQuotaMessage', '')

      if (!state.adminQuotaUser || !state.adminQuotaModel || !Number.isInteger(availableChecks) || availableChecks < 0) {
        commit('setAdminQuotaMessage', 'Введите пользователя, модель и количество')
        return
      }

      commit('setAdminQuotaLoading', true)
      try {
        const data = await documentCheckerApi.setUsageLimit(state.authToken, {
          user_email: state.adminQuotaUser,
          model: state.adminQuotaModel,
          available_checks: availableChecks,
        })
        commit('setAdminQuotaMessage', `Доступно: ${data.remaining ?? availableChecks} из ${data.usage_limit ?? availableChecks}`)
        await dispatch('loadModels').catch(() => {})
        await dispatch('loadAdminUsers').catch(() => {})
      } catch (error) {
        commit('setAdminQuotaMessage', error.message || 'Не удалось сохранить лимит')
      } finally {
        commit('setAdminQuotaLoading', false)
      }
    },
    async uploadAdminTemplate({ state, commit, dispatch }) {
      if (!state.adminTemplateFile) return

      commit('setAdminTemplateUploadLoading', true)
      commit('setAdminTemplateUploadMessage', '')

      try {
        const data = await documentCheckerApi.uploadAdminTemplate(state.authToken, state.adminTemplateFile)
        commit('setAdminTemplateUploadMessage', `Шаблон загружен: ${data.name}`)
        commit('setAdminTemplateFile', null)
        await dispatch('loadTemplates')
        commit('setSelectedTemplate', data.id)
      } catch (error) {
        commit('setAdminTemplateUploadMessage', error.message || 'Не удалось загрузить шаблон')
      } finally {
        commit('setAdminTemplateUploadLoading', false)
      }
    },
  },
}
