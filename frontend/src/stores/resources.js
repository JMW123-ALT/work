import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCategories } from '@/api/resources.js'

export const useResourcesStore = defineStore('resources', () => {
  const categories = ref([])
  const selectedResourceIds = ref([])
  const currentPlanningContext = ref('')

  async function loadCategories() {
    try {
      const data = await getCategories()
      categories.value = data.items || []
    } catch {
      categories.value = []
    }
  }

  function selectResource(id) {
    if (!selectedResourceIds.value.includes(id)) {
      selectedResourceIds.value.push(id)
    }
  }

  function deselectResource(id) {
    selectedResourceIds.value = selectedResourceIds.value.filter(x => x !== id)
  }

  function clearContext() {
    selectedResourceIds.value = []
    currentPlanningContext.value = ''
  }

  return { categories, selectedResourceIds, currentPlanningContext, loadCategories, selectResource, deselectResource, clearContext }
})
