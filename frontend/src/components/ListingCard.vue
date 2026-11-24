<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import api, { errorMessage, imageUrl } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { formatPrice, timeAgo } from '@/utils'

const props = defineProps({ listing: { type: Object, required: true } })
const emit = defineEmits(['wishlist-change'])

const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()
const saved = ref(!!props.listing.in_wishlist)
const busy = ref(false)

async function toggleWishlist() {
  if (!auth.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  busy.value = true
  try {
    if (saved.value) await api.delete(`/wishlist/${props.listing.id}`)
    else await api.post(`/wishlist/${props.listing.id}`)
    saved.value = !saved.value
    emit('wishlist-change', saved.value)
  } catch (error) {
    toast.error(errorMessage(error))
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <article class="listing-card card">
    <RouterLink :to="`/listings/${listing.id}`" class="image-link">
      <img v-if="listing.image" :src="imageUrl(listing.image)" :alt="listing.title" loading="lazy" />
      <div v-else class="no-image"><AppIcon name="image" :size="32" /></div>
      <span v-if="listing.status === 'sold'" class="sold-tag">SOLD</span>
      <span v-else-if="listing.status === 'reserved'" class="sold-tag reserved">RESERVED</span>
    </RouterLink>
    <button
      v-if="auth.user?.id !== listing.seller_id"
      class="heart"
      :class="{ saved }"
      :disabled="busy"
      :aria-label="saved ? 'Remove from wishlist' : 'Save to wishlist'"
      @click="toggleWishlist"
    >
      <AppIcon name="heart" :size="18" :filled="saved" />
    </button>
    <RouterLink :to="`/listings/${listing.id}`" class="body">
      <div class="price">{{ formatPrice(listing.price) }}</div>
      <h3 class="title">{{ listing.title }}</h3>
      <div class="meta">
        <span class="badge">{{ listing.condition_label }}</span>
      </div>
      <div class="foot tiny muted">
        <span class="truncate"><AppIcon name="pin" :size="13" /> {{ listing.location }}</span>
        <span>{{ timeAgo(listing.approved_at || listing.created_at) }}</span>
      </div>
    </RouterLink>
  </article>
</template>

<style scoped>
.listing-card { position: relative; overflow: hidden; display: flex; flex-direction: column; transition: box-shadow 0.15s, transform 0.15s; }
.listing-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.image-link { display: block; aspect-ratio: 4 / 3; background: #e9edf1; position: relative; }
.image-link img { width: 100%; height: 100%; object-fit: cover; }
.no-image { width: 100%; height: 100%; display: grid; place-items: center; color: #9aa5b1; }
.sold-tag { position: absolute; left: 10px; top: 10px; background: #1e40af; color: #fff; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; }
.sold-tag.reserved { background: #b45309; }
.heart { position: absolute; right: 10px; top: 10px; width: 34px; height: 34px; border-radius: 999px; border: none; background: rgba(255, 255, 255, 0.92); color: #334155; display: grid; place-items: center; cursor: pointer; box-shadow: var(--shadow); }
.heart.saved { color: var(--danger); }
.body { padding: 12px 14px 14px; color: var(--text); text-decoration: none !important; display: flex; flex-direction: column; gap: 4px; flex: 1; }
.price { font-size: 1.1rem; }
.title { font-size: 0.95rem; font-weight: 500; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.6em; }
.foot { display: flex; justify-content: space-between; gap: 8px; margin-top: auto; padding-top: 4px; }
.foot span:first-child { display: inline-flex; align-items: center; gap: 3px; }
</style>
