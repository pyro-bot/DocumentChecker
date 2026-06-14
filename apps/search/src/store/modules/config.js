import * as documentCheckerApi from '../../services/documentCheckerApi'

export const configStore = {
  state: () => ({
    models: [],
    templates: [],
    model: '',
    usageResetIntervalHours: null,
  }),

  mutations: {
    setModels(state, data) {
      state.models = data.models || []
      state.usageResetIntervalHours = data.usage_limit_reset_interval_hours ?? null

      if (!state.models.some((item) => item.id === state.model)) {
        state.model = data.default_model || state.models[0]?.id || ''
      }
      if (!state.models.some((item) => item.id === state.adminQuotaModel)) {
        state.adminQuotaModel = data.default_model || state.models[0]?.id || ''
      }
    },
    setModel(state, model) {
      state.model = model
    },
    setTemplates(state, templates) {
      state.templates = templates || []
      if (state.selectedTemplate && !state.templates.some((item) => item.id === state.selectedTemplate)) {
        state.selectedTemplate = ''
      }
    },
  },

  actions: {
    async loadModels({ state, commit }) {
      commit('setModels', await documentCheckerApi.fetchModels(state.authToken))
    },
    async loadTemplates({ state, commit }) {
      const data = await documentCheckerApi.fetchTemplates(state.authToken)
      commit('setTemplates', data.templates || [])
    },
  },
}
