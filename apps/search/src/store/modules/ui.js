export const uiStore = {
  state: () => ({
    globalError: '',
  }),

  mutations: {
    setGlobalError(state, value) {
      state.globalError = value
    },
  },
}
