import * as documentCheckerApi from '../../services/documentCheckerApi'
import { renderMarkdown } from '../../utils/markdown'
import { isMarkdownTemplate } from '../../utils/templates'

export const templatePreviewStore = {
  state: () => ({
    templatePreviewOpen: false,
    templatePreviewLoading: false,
    templatePreviewSaving: false,
    templatePreviewEditing: false,
    templatePreviewError: '',
    templatePreviewTemplate: null,
    templatePreviewContent: '',
  }),

  getters: {
    renderedTemplateMarkdown: (state) => renderMarkdown(state.templatePreviewContent),
  },

  mutations: {
    openTemplatePreview(state, { template, editing }) {
      state.templatePreviewOpen = true
      state.templatePreviewEditing = Boolean(editing && state.currentUser?.role === 'admin')
      state.templatePreviewLoading = true
      state.templatePreviewSaving = false
      state.templatePreviewError = ''
      state.templatePreviewTemplate = template
    },
    closeTemplatePreview(state) {
      if (state.templatePreviewSaving) return
      state.templatePreviewOpen = false
      state.templatePreviewLoading = false
      state.templatePreviewEditing = false
      state.templatePreviewError = ''
    },
    setTemplatePreviewLoading(state, value) {
      state.templatePreviewLoading = value
    },
    setTemplatePreviewSaving(state, value) {
      state.templatePreviewSaving = value
    },
    setTemplatePreviewEditing(state, value) {
      state.templatePreviewEditing = value
    },
    setTemplatePreviewError(state, value) {
      state.templatePreviewError = value
    },
    setTemplatePreviewContent(state, value) {
      state.templatePreviewContent = value
    },
    setTemplatePreviewTemplate(state, template) {
      state.templatePreviewTemplate = template
    },
  },

  actions: {
    async openTemplatePreview({ state, getters, commit }, editing = false) {
      const template = getters.selectedTemplateMeta
      if (!isMarkdownTemplate(template)) return

      commit('openTemplatePreview', { template, editing })

      try {
        const data = await documentCheckerApi.fetchTemplateMarkdown(state.authToken, template.id)
        commit('setTemplatePreviewTemplate', data)
        commit('setTemplatePreviewContent', data.content || '')
      } catch (error) {
        commit('setTemplatePreviewError', error.message || 'Не удалось открыть шаблон')
        commit('setTemplatePreviewContent', '')
      } finally {
        commit('setTemplatePreviewLoading', false)
      }
    },
    async saveTemplateMarkdown({ state, commit, dispatch }) {
      const templateId = state.templatePreviewTemplate?.id || state.selectedTemplate
      if (!templateId || state.currentUser?.role !== 'admin') return

      commit('setTemplatePreviewSaving', true)
      commit('setTemplatePreviewError', '')

      try {
        const data = await documentCheckerApi.saveTemplateMarkdown(state.authToken, templateId, state.templatePreviewContent)
        await dispatch('loadTemplates')
        commit('setSelectedTemplate', data.id)
        commit('setTemplatePreviewTemplate', data)
        commit('setTemplatePreviewEditing', false)
        commit('setAdminTemplateUploadMessage', `Шаблон сохранён: ${data.name}`)
      } catch (error) {
        commit('setTemplatePreviewError', error.message || 'Не удалось сохранить шаблон')
      } finally {
        commit('setTemplatePreviewSaving', false)
      }
    },
  },
}
