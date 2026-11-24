<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import ToastHost from '@/components/ToastHost.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
let timer = null

// Keep the message / notification badges fresh.
onMounted(() => {
  timer = setInterval(() => auth.refreshSummary(), 30000)
})
onUnmounted(() => clearInterval(timer))
watch(() => route.fullPath, () => auth.refreshSummary())
</script>

<template>
  <NavBar />
  <main>
    <RouterView v-if="auth.ready" :key="route.name === 'messages' ? 'messages' : route.path" />
    <div v-else class="spinner" aria-label="Loading"></div>
  </main>
  <footer class="site-footer">
    <div class="container row between">
      <span>© {{ new Date().getFullYear() }} ResaleIQ — buy and sell pre-owned items across Bangladesh.</span>
      <span class="muted">Vue.js · Flask · SQLite</span>
    </div>
  </footer>
  <ToastHost />
</template>

<style>
.site-footer { border-top: 1px solid var(--border); background: #fff; padding: 18px 0; font-size: 0.85rem; color: var(--muted); }
main { min-height: calc(100vh - 64px - 58px); }
</style>
