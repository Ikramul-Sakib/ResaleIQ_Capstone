<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pages: { type: Number, required: true },
})
const emit = defineEmits(['change'])

const visible = computed(() => {
  const list = []
  const start = Math.max(1, props.page - 2)
  const end = Math.min(props.pages, start + 4)
  for (let p = Math.max(1, end - 4); p <= end; p++) list.push(p)
  return list
})
</script>

<template>
  <nav v-if="pages > 1" class="pagination" aria-label="Pages">
    <button class="btn btn-sm" :disabled="page <= 1" @click="emit('change', page - 1)">Previous</button>
    <button
      v-for="p in visible"
      :key="p"
      class="btn btn-sm"
      :class="{ 'btn-primary': p === page }"
      :aria-current="p === page ? 'page' : undefined"
      @click="emit('change', p)"
    >{{ p }}</button>
    <button class="btn btn-sm" :disabled="page >= pages" @click="emit('change', page + 1)">Next</button>
  </nav>
</template>

<style scoped>
.pagination { display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; margin-top: 24px; }
</style>
