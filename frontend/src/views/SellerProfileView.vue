<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api, { errorMessage } from '@/api'
import ListingCard from '@/components/ListingCard.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import StarRating from '@/components/StarRating.vue'
import { formatDate, timeAgo } from '@/utils'

const route = useRoute()
const seller = ref(null)
const stats = ref({})
const listings = ref({ items: [], page: 1, pages: 0 })
const reviews = ref({ items: [], total: 0 })
const loading = ref(true)
const error = ref('')

async function loadListings(page = 1) {
  const { data } = await api.get('/listings', { params: { seller_id: route.params.id, page, per_page: 12 } })
  listings.value = data
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/users/${route.params.id}`)
    seller.value = data.user
    stats.value = data.stats
    await loadListings()
    reviews.value = (await api.get(`/users/${route.params.id}/reviews`, { params: { per_page: 10 } })).data
  } catch (err) {
    error.value = err.response?.status === 404 ? 'This seller was not found.' : errorMessage(err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container page">
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="error" class="empty card"><h3>{{ error }}</h3></div>
    <template v-else>
      <div class="card card-body profile mb">
        <span class="avatar">{{ seller.name.charAt(0).toUpperCase() }}</span>
        <div>
          <h1>{{ seller.name }}</h1>
          <p class="muted small">
            <span v-if="seller.location">{{ seller.location }} · </span>Member since {{ formatDate(seller.member_since) }}
            · {{ stats.active_listings }} active · {{ stats.sold_listings }} sold
          </p>
          <p v-if="stats.rating_count" class="small" style="margin-bottom: 4px">
            <StarRating :model-value="stats.rating_avg" /> <strong>{{ stats.rating_avg }}</strong>
            <span class="muted"> from {{ stats.rating_count }} review{{ stats.rating_count === 1 ? '' : 's' }}</span>
          </p>
          <p v-else class="tiny muted" style="margin-bottom: 4px">No reviews yet</p>
          <p v-if="seller.bio" style="margin: 0">{{ seller.bio }}</p>
        </div>
      </div>
      <h2>Listings</h2>
      <div v-if="!listings.items.length" class="empty card"><p>No active listings right now.</p></div>
      <div v-else class="listing-grid">
        <ListingCard v-for="item in listings.items" :key="item.id" :listing="item" />
      </div>
      <PaginationBar :page="listings.page" :pages="listings.pages" @change="loadListings" />

      <template v-if="reviews.items.length">
        <h2 class="mt">Reviews from buyers</h2>
        <div class="card">
          <div v-for="review in reviews.items" :key="review.id" class="review">
            <div class="row between">
              <span><StarRating :model-value="review.rating" :size="14" /> <strong class="small">{{ review.reviewer?.name }}</strong></span>
              <span class="tiny muted">{{ timeAgo(review.created_at) }}</span>
            </div>
            <p v-if="review.comment" class="small" style="margin: 6px 0 2px">{{ review.comment }}</p>
            <div class="tiny muted">Bought: {{ review.listing_title }}</div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.profile { display: flex; gap: 16px; align-items: center; }
.review { padding: 12px 16px; border-bottom: 1px solid var(--border); }
.review:last-child { border-bottom: none; }
.avatar { width: 64px; height: 64px; border-radius: 999px; background: var(--primary-soft); color: var(--primary-dark); display: grid; place-items: center; font-weight: 800; font-size: 1.6rem; flex-shrink: 0; }
</style>
