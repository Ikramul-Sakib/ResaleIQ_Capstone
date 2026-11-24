<script setup>
import AppIcon from './AppIcon.vue'

// Display stars, or pick a rating when `editable` (use with v-model).
const model = defineModel({ type: Number, default: 0 })
defineProps({
  editable: { type: Boolean, default: false },
  size: { type: Number, default: 16 },
})
</script>

<template>
  <span class="stars" :class="{ editable }" :aria-label="`${model} out of 5 stars`">
    <template v-if="editable">
      <button v-for="n in 5" :key="n" type="button" :aria-label="`${n} star${n > 1 ? 's' : ''}`" @click="model = n">
        <AppIcon name="star" :size="size" :filled="n <= model" />
      </button>
    </template>
    <template v-else>
      <AppIcon v-for="n in 5" :key="n" name="star" :size="size" :filled="n <= Math.round(model)" />
    </template>
  </span>
</template>

<style scoped>
.stars { display: inline-flex; gap: 1px; color: #f59e0b; vertical-align: middle; }
.stars button { background: none; border: none; padding: 2px; cursor: pointer; color: #f59e0b; }
.stars button:hover { transform: scale(1.15); }
</style>
