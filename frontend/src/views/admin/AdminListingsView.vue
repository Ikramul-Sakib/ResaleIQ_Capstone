<script setup>
import { onMounted, ref, watch } from 'vue'
import api, { errorMessage, imageUrl } from '@/api'
import AdminNav from '@/components/AdminNav.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useToastStore } from '@/stores/toast'
import { formatPrice, timeAgo } from '@/utils'

const toast = useToastStore()
const status = ref('pending')
const search = ref('')
const page = ref(1)
const data = ref({ items: [], page: 1, pages: 0, total: 0 })
const loading = ref(true)
const error = ref('')
const dialog = ref(null) // { type: 'reject' | 'remove', listing }
const reason = ref('')
const working = ref(false)

const statuses = [
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Live' },
  { key: 'reserved', label: 'Reserved' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'sold', label: 'Sold' },
  { key: 'removed', label: 'Removed' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await api.get('/admin/listings', { params: { status: status.value, q: search.value, page: page.value } })).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function approve(listing) {
  try {
    await api.post(`/admin/listings/${listing.id}/approve`)
    toast.show(`"${listing.title}" is now live.`)
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

function openDialog(type, listing) {
  dialog.value = { type, listing }
  reason.value = ''
}

async function submitDialog() {
  working.value = true
  try {
    await api.post(`/admin/listings/${dialog.value.listing.id}/${dialog.value.type}`, { reason: reason.value })
    toast.show(dialog.value.type === 'reject' ? 'Listing rejected. The seller was notified.' : 'Listing removed. The seller was notified.')
    dialog.value = null
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    working.value = false
  }
}

watch(status, () => {
  page.value = 1
  load()
})
onMounted(load)
</script>

<template>
  <div class="container page">
    <AdminNav />
    <div class="row between mb">
      <div class="row">
        <button v-for="s in statuses" :key="s.key" class="chip" :class="{ active: status === s.key }" @click="status = s.key">{{ s.label }}</button>
      </div>
      <form class="row" @submit.prevent="page = 1; load()">
        <input v-model="search" class="input" type="search" placeholder="Search titles" style="width: 220px" />
        <button class="btn">Search</button>
      </form>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="!data.items.length" class="empty card">
      <h3>{{ status === 'pending' ? 'All caught up!' : 'No listings' }}</h3>
      <p v-if="status === 'pending'">There are no listings waiting for review.</p>
    </div>
    <div v-else class="list">
      <article v-for="listing in data.items" :key="listing.id" class="card review">
        <div class="photos">
          <a v-for="image in listing.images" :key="image.id" :href="imageUrl(image.url)" target="_blank" rel="noopener">
            <img :src="imageUrl(image.url)" alt="" />
          </a>
        </div>
        <div class="details">
          <div class="row between">
            <h3 style="margin: 0">{{ listing.title }}</h3>
            <StatusBadge :status="listing.status" />
          </div>
          <div class="row small">
            <span class="price">{{ formatPrice(listing.price) }}</span>
            <span class="badge">{{ listing.category?.name }}</span>
            <span class="badge">{{ listing.condition_label }}</span>
            <span class="muted">{{ listing.location }}</span>
          </div>
          <p class="small desc">{{ listing.description }}</p>
          <div class="tiny muted">
            Seller: <RouterLink :to="`/sellers/${listing.seller.id}`">{{ listing.seller.name }}</RouterLink>
            · <span v-if="listing.brand">{{ listing.brand }} {{ listing.model }} · </span>updated {{ timeAgo(listing.updated_at) }}
          </div>
          <div v-if="listing.rejection_reason" class="tiny reason">Reason: {{ listing.rejection_reason }}</div>
          <div class="row mt">
            <button v-if="['pending', 'rejected'].includes(listing.status)" class="btn btn-primary btn-sm" @click="approve(listing)">Approve</button>
            <button v-if="listing.status === 'pending'" class="btn btn-sm" @click="openDialog('reject', listing)">Reject</button>
            <button v-if="!['removed'].includes(listing.status)" class="btn btn-sm btn-ghost" @click="openDialog('remove', listing)">Remove</button>
            <RouterLink :to="`/listings/${listing.id}`" class="btn btn-sm btn-ghost">Open</RouterLink>
          </div>
        </div>
      </article>
    </div>
    <PaginationBar :page="data.page" :pages="data.pages" @change="(p) => { page = p; load() }" />

    <ModalDialog v-if="dialog" :title="dialog.type === 'reject' ? 'Reject listing' : 'Remove listing'" @close="dialog = null">
      <p class="small muted">{{ dialog.listing.title }}</p>
      <div class="form-group">
        <label for="reason">Reason (sent to the seller)</label>
        <textarea id="reason" v-model="reason" class="input" rows="3" maxlength="500" placeholder="e.g. Photos don't show the actual item."></textarea>
      </div>
      <template #footer>
        <button class="btn" @click="dialog = null">Cancel</button>
        <button class="btn btn-danger" :disabled="working || reason.trim().length < 5" @click="submitDialog">
          {{ dialog.type === 'reject' ? 'Reject' : 'Remove' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 12px; }
.review { display: grid; grid-template-columns: 260px 1fr; gap: 16px; padding: 14px; }
.photos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; align-content: start; }
.photos a:first-child { grid-column: 1 / -1; }
.photos img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 6px; background: #e9edf1; }
.details { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.desc { white-space: pre-line; margin: 4px 0; max-height: 7.5em; overflow: auto; }
.reason { color: var(--danger); }
@media (max-width: 720px) {
  .review { grid-template-columns: 1fr; }
}
</style>
