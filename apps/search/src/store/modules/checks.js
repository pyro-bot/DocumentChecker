import * as documentCheckerApi from '../../services/documentCheckerApi'
import { downloadJson } from '../../services/downloadService'
import { buildGroupedErrors } from '../../utils/results'

function createInitialFileResult(file) {
  return {
    fileName: file.name,
    file,
    open: false,
    loading: true,
    bibliographyLoading: false,
    bibliographyError: null,
    bibliographyResult: null,
    error: null,
    result: null,
    groupedErrors: buildGroupedErrors([]),
  }
}

export const checksStore = {
  state: () => ({
    loading: false,
    progressLabel: '',
    fileResults: [],
  }),

  getters: {
    canRun: (state, getters) => getters.hasTemplate && state.files.documents.length > 0 && Boolean(state.model),
    overallProgress: (state) => {
      if (!state.fileResults.length) return 0
      const done = state.fileResults.filter((fileResult) => !fileResult.loading && !fileResult.bibliographyLoading).length
      return Math.round((done / state.fileResults.length) * 100)
    },
  },

  mutations: {
    setLoading(state, value) {
      state.loading = value
    },
    setProgressLabel(state, value) {
      state.progressLabel = value
    },
    setFileResults(state, results) {
      state.fileResults = results
    },
    setFileResultData(state, { fileResult, data }) {
      fileResult.result = data
      fileResult.groupedErrors = buildGroupedErrors(data.errors ?? [])
      fileResult.loading = false
    },
    setFileResultError(state, { fileResult, error }) {
      fileResult.error = error
    },
    setFileResultLoading(state, { fileResult, loading }) {
      fileResult.loading = loading
    },
    toggleFileResultOpen(state, fileResult) {
      fileResult.open = !fileResult.open
    },
    setBibliographyLoading(state, { fileResult, loading }) {
      fileResult.bibliographyLoading = loading
    },
    setBibliographyResult(state, { fileResult, result }) {
      fileResult.bibliographyResult = result
    },
    setBibliographyError(state, { fileResult, error }) {
      fileResult.bibliographyError = error
    },
    resetBibliography(state, fileResult) {
      fileResult.bibliographyError = null
      fileResult.bibliographyResult = null
    },
  },

  actions: {
    async runCheck({ state, commit, dispatch }) {
      commit('setLoading', true)
      commit('setGlobalError', '')
      commit('setFileResults', state.files.documents.map(createInitialFileResult))
      commit('setProgressLabel', `Проверяем ${state.files.documents.length} документов...`)

      for (const fileResult of state.fileResults) {
        await dispatch('checkSingleFile', fileResult)
      }

      await dispatch('loadModels').catch(() => {})
      await dispatch('loadHistory').catch(() => {})
      if (state.currentUser?.role === 'admin') {
        await dispatch('loadAdminData').catch(() => {})
      }
      commit('setLoading', false)
      commit('setProgressLabel', 'Готово')
    },
    async checkSingleFile({ state, commit, dispatch }, fileResult) {
      try {
        const data = await documentCheckerApi.validateUpload(state.authToken, {
          selectedTemplate: state.selectedTemplate,
          templateFile: state.files.template,
          documentFile: fileResult.file,
          model: state.model,
        })
        if (data.error) throw new Error(data.error)

        commit('setFileResultData', { fileResult, data })
        await dispatch('checkBibliographyForFile', fileResult)
      } catch (error) {
        if (error.status === 401) {
          commit('clearAuth')
          commit('setFileResultError', { fileResult, error: 'Ошибка: Сессия истекла' })
          return
        }
        commit('setFileResultError', { fileResult, error: `Ошибка: ${error.message}` })
      } finally {
        commit('setFileResultLoading', { fileResult, loading: false })
      }
    },
    async checkBibliographyForFile({ state, commit }, fileResult) {
      commit('setBibliographyLoading', { fileResult, loading: true })
      commit('resetBibliography', fileResult)

      try {
        const result = await documentCheckerApi.checkBibliographyUpload(
          state.authToken,
          fileResult.file,
          30,
          fileResult.result?.check_id,
        )
        commit('setBibliographyResult', { fileResult, result })
      } catch (error) {
        if (error.status === 401) {
          commit('clearAuth')
          commit('setBibliographyError', { fileResult, error: 'Ошибка проверки источников: Сессия истекла' })
          return
        }
        commit('setBibliographyError', { fileResult, error: `Ошибка проверки источников: ${error.message}` })
      } finally {
        commit('setBibliographyLoading', { fileResult, loading: false })
      }
    },
    async downloadReport({ state, dispatch }, fileResult) {
      if (!fileResult.result) return
      if (fileResult.result.check_id) {
        await dispatch('downloadHistoryReport', { id: fileResult.result.check_id, document_name: fileResult.fileName })
        return
      }
      downloadJson({
        template: state.selectedTemplate || state.files.template?.name,
        document: fileResult.fileName,
        model: state.model,
        result: fileResult.result,
        bibliography_result: fileResult.bibliographyResult,
        timestamp: new Date().toISOString(),
        checked_formatting: true,
      }, `report_${fileResult.fileName.replace('.docx', '')}_${Date.now()}.json`)
    },
  },
}
