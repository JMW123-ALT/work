<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app.js'

const appStore = useAppStore()
onMounted(() => appStore.startHealthCheck())
</script>
