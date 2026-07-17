import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCategories } from '@/api/resources.js'

export const useResourcesStore = defineStore('resources', () => {
  const categories = ref([])
  const selectedResourceIds = ref([])
  const currentPlanningContext = ref('')

  // ── 资料查询持久化状态（切页不丢失，直到新查询） ──
  const searchQuery = ref('')
  const searchTopK = ref(5)
  const searchMinConf = ref(0.3)
  const searchResults = ref([])
  const searchSearched = ref(false)
  const searchPermissionNotice = ref('')
  const searchSelectedIds = ref(new Set())

  async function loadCategories() {
    try {
      const data = await getCategories()
      categories.value = data.items || []
    } catch {
      categories.value = []
    }
  }

  function selectResource(id) {
    if (!selectedResourceIds.value.includes(id)) selectedResourceIds.value.push(id)
  }
  function deselectResource(id) {
    selectedResourceIds.value = selectedResourceIds.value.filter(x => x !== id)
  }
  function clearContext() {
    selectedResourceIds.value = []
    currentPlanningContext.value = ''
  }

  return {
    categories, selectedResourceIds, currentPlanningContext,
    loadCategories, selectResource, deselectResource, clearContext,
    searchQuery, searchTopK, searchMinConf,
    searchResults, searchSearched, searchPermissionNotice, searchSelectedIds,
  }
})
