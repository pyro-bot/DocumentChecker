import * as documentCheckerApi from '../../services/documentCheckerApi'
import { downloadBlob } from '../../services/downloadService'
import { normalizeHistoryItem } from '../../utils/results'

export const historyStore = {
  state: () => ({
    historyItems: [],
  }),

  mutations: {
    setHistoryItems(state, items) {
      state.historyItems = (items || []).map(normalizeHistoryItem)
    },
    toggleHistoryItemOpen(state, item) {
      item.open = !item.open
    },
  },

  actions: {
    async loadHistory({ state, commit }, options = {}) {
      const data = await documentCheckerApi.fetchHistory(state.authToken, options)
      commit('setHistoryItems', data.checks || [])
    },
    async downloadHistoryReport({ state, commit }, item) {
      try {
        const file = await documentCheckerApi.downloadHistoryReport(state.authToken, item)
        downloadBlob(file.blob, file.filename)
      } catch (error) {
        commit('setGlobalError', error.message || 'Не удалось скачать отчет')
      }
    },
    async downloadHistorySource({ state, commit }, item) {
      try {
        const file = await documentCheckerApi.downloadHistorySource(state.authToken, item)
        downloadBlob(file.blob, file.filename)
      } catch (error) {
        commit('setGlobalError', error.message || 'Не удалось скачать исходный файл')
      }
    },
    async downloadHistoryTemplate({ state, commit }, item) {
      try {
        const file = await documentCheckerApi.downloadHistoryTemplate(state.authToken, item)
        downloadBlob(file.blob, file.filename)
      } catch (error) {
        commit('setGlobalError', error.message || 'Не удалось скачать шаблон')
      }
    },
  },
}
