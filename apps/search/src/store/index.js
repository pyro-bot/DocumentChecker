import { createStore } from 'vuex'
import { adminStore } from './modules/admin'
import { authStore } from './modules/auth'
import { checksStore } from './modules/checks'
import { configStore } from './modules/config'
import { historyStore } from './modules/history'
import { templatePreviewStore } from './modules/templatePreview'
import { uploadsStore } from './modules/uploads'
import { uiStore } from './modules/ui'

const storeParts = [
  authStore,
  uiStore,
  uploadsStore,
  configStore,
  checksStore,
  historyStore,
  adminStore,
  templatePreviewStore,
]

function mergeState(parts) {
  return () => Object.assign({}, ...parts.map((part) => part.state?.() || {}))
}

function mergeOption(parts, key) {
  return Object.assign({}, ...parts.map((part) => part[key] || {}))
}

export default createStore({
  state: mergeState(storeParts),
  getters: mergeOption(storeParts, 'getters'),
  mutations: mergeOption(storeParts, 'mutations'),
  actions: mergeOption(storeParts, 'actions'),
})
