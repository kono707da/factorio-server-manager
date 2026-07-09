import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
    },
    {
      path: '/logs',
      name: 'Logs',
      component: () => import('@/views/LogsView.vue'),
    },
    {
      path: '/commands',
      name: 'Commands',
      component: () => import('@/views/CommandsView.vue'),
    },
    {
      path: '/saves',
      name: 'Saves',
      component: () => import('@/views/SavesView.vue'),
    },
    {
      path: '/backups',
      name: 'Backups',
      component: () => import('@/views/BackupsView.vue'),
    },
    {
      path: '/versions',
      name: 'Versions',
      component: () => import('@/views/VersionsView.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
    },
  ],
})

export default router
