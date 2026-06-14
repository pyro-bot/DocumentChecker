import { isMarkdownTemplate } from '../../utils/templates'

export const uploadsStore = {
  state: () => ({
    files: { template: null, documents: [] },
    selectedTemplate: '',
  }),

  getters: {
    hasTemplate: (state) => Boolean(state.files.template || state.selectedTemplate),
    selectedTemplateMeta: (state) => state.templates.find((item) => item.id === state.selectedTemplate) || null,
    canPreviewSelectedTemplate: (state, getters) => isMarkdownTemplate(getters.selectedTemplateMeta),
  },

  mutations: {
    addDocuments(state, files) {
      for (const file of files) {
        if (!state.files.documents.find((item) => item.name === file.name)) {
          state.files.documents.push(file)
        }
      }
    },
    removeDocument(state, index) {
      state.files.documents.splice(index, 1)
    },
    setTemplateFile(state, file) {
      state.selectedTemplate = ''
      state.files.template = file
    },
    clearTemplateFile(state) {
      state.files.template = null
    },
    setSelectedTemplate(state, templateId) {
      state.selectedTemplate = templateId
      state.files.template = null
    },
  },
}
