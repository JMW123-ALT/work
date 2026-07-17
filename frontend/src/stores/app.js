import { defineStore } from 'pinia'
import { ref } from 'vue'
import { checkHealth } from '@/api/chat.js'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const backendHealthy = ref(null) // null=checking, true=ok, false=offline
  const currentUserType = ref('internal')

  let healthTimer = null

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  async function doHealthCheck() {
    try {
      await checkHealth()
      backendHealthy.value = true
    } catch {
      backendHealthy.value = false
    }
  }

  function startHealthCheck() {
    doHealthCheck()
    healthTimer = setInterval(doHealthCheck, 30_000)
  }

  function stopHealthCheck() {
    if (healthTimer) clearInterval(healthTimer)
  }

  function setUserType(type) {
    currentUserType.value = type
  }

  return { sidebarCollapsed, backendHealthy, currentUserType, toggleSidebar, startHealthCheck, stopHealthCheck, setUserType }
})
