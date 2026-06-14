import './style.css'
import { createApp, defineComponent, h } from 'vue'
import { createRouter, createWebHistory, RouterView } from 'vue-router'
import DocumentChecker from './DocumentChecker.vue'
import JsonReportViewer from './JsonReportViewer.vue'
import store from './store'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DocumentChecker },
    { path: '/report', component: JsonReportViewer },
  ],
})

const App = defineComponent({ render: () => h(RouterView) })

createApp(App).use(store).use(router).mount('#app')
