<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  LayoutDashboard,
  ScrollText,
  Terminal,
  Save,
  HardDrive,
  RefreshCw,
  Package,
  Settings,
  Menu,
  X,
  Factory,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const sidebarOpen = ref(false)

const navItems = [
  { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { path: '/logs', label: '日志查看', icon: ScrollText },
  { path: '/commands', label: '一键指令', icon: Terminal },
  { path: '/saves', label: '存档管理', icon: Save },
  { path: '/backups', label: '定时备份', icon: HardDrive },
  { path: '/versions', label: '版本管理', icon: RefreshCw },
  { path: '/mods', label: 'Mod 管理', icon: Package },
  { path: '/settings', label: '系统设置', icon: Settings },
]

function navigate(path: string) {
  router.push(path)
  sidebarOpen.value = false
}
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Mobile overlay -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-black/60 z-40 lg:hidden"
      @click="sidebarOpen = false"
    />

    <!-- Sidebar -->
    <aside
      :class="[
        'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-factorio-surface border-r border-factorio-border flex flex-col transition-transform duration-300',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      ]"
    >
      <!-- Logo -->
      <div class="h-16 flex items-center gap-3 px-5 border-b border-factorio-border">
        <div class="w-9 h-9 rounded-lg bg-factorio-accent flex items-center justify-center">
          <Factory class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="font-display font-bold text-lg text-factorio-text leading-tight">Factorio</h1>
          <p class="text-[10px] text-factorio-text-muted leading-none tracking-wider uppercase">Server Manager</p>
        </div>
        <button class="ml-auto lg:hidden text-factorio-text-muted hover:text-factorio-text" @click="sidebarOpen = false">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigate(item.path)"
          :class="[
            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
            route.path === item.path
              ? 'bg-factorio-accent/15 text-factorio-accent glow-accent'
              : 'text-factorio-text-muted hover:bg-factorio-card hover:text-factorio-text'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5" />
          {{ item.label }}
        </button>
      </nav>

      <!-- Footer -->
      <div class="p-4 border-t border-factorio-border">
        <p class="text-xs text-factorio-text-muted text-center">Factorio Server Manager v1.0</p>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Top bar -->
      <header class="h-14 bg-factorio-surface border-b border-factorio-border flex items-center px-4 lg:px-6 shrink-0">
        <button class="lg:hidden text-factorio-text-muted hover:text-factorio-text mr-3" @click="sidebarOpen = true">
          <Menu class="w-5 h-5" />
        </button>
        <h2 class="font-display font-semibold text-lg text-factorio-text">
          {{ navItems.find(i => i.path === route.path)?.label || 'Factorio Server Manager' }}
        </h2>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-4 lg:p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
