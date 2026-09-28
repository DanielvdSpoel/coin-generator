import { createRouter, createWebHistory } from 'vue-router'

import DesignerView from '@/views/DesignerView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [{ path: '/', name: 'designer', component: DesignerView }],
})

export default router
