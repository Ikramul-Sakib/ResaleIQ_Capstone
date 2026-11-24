<script setup>
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="toasts" aria-live="polite">
    <div v-for="item in toast.items" :key="item.id" class="toast" :class="item.type" @click="toast.dismiss(item.id)">
      {{ item.message }}
    </div>
  </div>
</template>

<style scoped>
.toasts { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; gap: 8px; z-index: 200; width: min(420px, calc(100vw - 32px)); }
.toast { padding: 12px 16px; border-radius: 10px; background: #0f172a; color: #fff; box-shadow: var(--shadow-lg); font-size: 0.93rem; cursor: pointer; }
.toast.success { background: #14532d; }
.toast.error { background: #991b1b; }
</style>
