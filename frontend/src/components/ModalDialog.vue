<script setup>
import { onMounted, onUnmounted } from 'vue'
import AppIcon from './AppIcon.vue'

defineProps({ title: { type: String, required: true } })
const emit = defineEmits(['close'])

function onKey(event) {
  if (event.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="emit('close')">
      <div class="modal card" role="dialog" aria-modal="true" :aria-label="title">
        <div class="modal-head">
          <h2>{{ title }}</h2>
          <button class="btn btn-ghost btn-icon" aria-label="Close" @click="emit('close')"><AppIcon name="close" /></button>
        </div>
        <div class="modal-body"><slot /></div>
        <div v-if="$slots.footer" class="modal-foot"><slot name="footer" /></div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); display: grid; place-items: center; padding: 16px; z-index: 100; }
.modal { width: 100%; max-width: 480px; box-shadow: var(--shadow-lg); max-height: calc(100vh - 32px); overflow-y: auto; }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px 6px 20px; }
.modal-head h2 { margin: 0; font-size: 1.1rem; }
.modal-body { padding: 8px 20px 16px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 20px 18px; }
</style>
