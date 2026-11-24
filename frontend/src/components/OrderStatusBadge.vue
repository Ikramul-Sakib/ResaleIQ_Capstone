<script setup>
import { ORDER_STATUS } from '@/utils'

defineProps({ status: { type: String, required: true } })
</script>

<template>
  <span class="badge" :class="`badge-${ORDER_STATUS[status]?.css || 'pending'}`">{{ ORDER_STATUS[status]?.label || status }}</span>
</template>
