<script setup>
import { onMounted, ref } from 'vue'
import api, { errorMessage } from '@/api'
import ListingCard from '@/components/ListingCard.vue'

const items = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    items.value = (await api.get('/wishlist')).data.items
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
})

function onChange(listing, saved) {
  if (!saved) items.value = items.value.filter((item) => item.id !== listing.id)
}
</script>

<template>
  <div class="container page">
    <div class="page-header">
      <div>
        <h1>Wishlist</h1>
        <p>Items you saved for later.</p>
      </div>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="!items.length" class="empty card">
      <h3>Your wishlist is empty</h3>
      <p>Tap the heart on any listing to save it here.</p>
      <RouterLink to="/" class="btn btn-primary">Browse items</RouterLink>
    </div>
    <div v-else class="listing-grid">
      <ListingCard v-for="item in items" :key="item.id" :listing="item" @wishlist-change="(saved) => onChange(item, saved)" />
    </div>
  </div>
</template>
