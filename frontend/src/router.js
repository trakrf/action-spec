import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './components/Dashboard.vue'
import PodForm from './components/PodForm.vue'
import SuccessPage from './components/SuccessPage.vue'
import ErrorPage from './components/ErrorPage.vue'

const routes = [
  { path: '/', name: 'home', component: Dashboard },
  { path: '/pod/new', name: 'new-pod', component: PodForm },
  { path: '/pod/:customer/:env', name: 'edit-pod', component: PodForm },
  { path: '/success', name: 'success', component: SuccessPage },
  { path: '/error', name: 'error', component: ErrorPage }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
