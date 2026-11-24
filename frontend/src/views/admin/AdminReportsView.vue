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
const status = ref('open')
const page = ref(1)
const data = ref({ items: [], page: 1, pages: 0 })
const loading = ref(true)
const error = ref('')
const removeTarget = ref(null)
const reason = ref('')
const working = ref(false)

async function load() {
  loading.value = true
  try {
    data.value = (await api.get('/admin/reports', { params: { status: status.value, page: page.value } })).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function update(report, action) {
  try {
    await api.post(`/admin/reports/${report.id}/${action}`)
    toast.show(action === 'dismiss' ? 'Report dismissed.' : 'Report marked as resolved.')
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

function openRemove(report) {
  removeTarget.value = report
  reason.value = `Removed after a report: ${report.reason_label}.`
}

async function removeListing() {
  working.value = true
  try {
    await api.post(`/admin/listings/${removeTarget.value.listing.id}/remove`, { reason: reason.value })
    toast.show('Listing removed and related reports resolved.')
    removeTarget.value = null
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
    <div class="row mb">
      <button v-for="s in ['open', 'resolved', 'dismissed']" :key="s" class="chip" :class="{ active: status === s }" @click="status = s">
        {{ s.charAt(0).toUpperCase() + s.slice(1) }}
      </button>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="!data.items.length" class="empty card">
      <h3>No {{ status }} reports</h3>
    </div>
    <div v-else class="list">
      <article v-for="report in data.items" :key="report.id" class="card report">
        <RouterLink v-if="report.listing" :to="`/listings/${report.listing.id}`" class="listing">
          <img class="thumb" :src="imageUrl(report.listing.image)" alt="" />
          <div class="min0">
            <strong class="truncate">{{ report.listing.title }}</strong>
            <div class="tiny muted">{{ formatPrice(report.listing.price) }} · <StatusBadge :status="report.listing.status" /></div>
          </div>
        </RouterLink>
        <div class="body">
          <div><span class="badge badge-rejected">{{ report.reason_label }}</span>
            <span class="tiny muted"> by {{ report.reporter?.name }} · {{ timeAgo(report.created_at) }}</span></div>
          <p v-if="report.details" class="small" style="margin: 6px 0 0">{{ report.details }}</p>
        </div>
        <div v-if="report.status === 'open'" class="actions">
          <button v-if="report.listing?.status !== 'removed'" class="btn btn-danger btn-sm" @click="openRemove(report)">Remove listing</button>
          <button class="btn btn-sm" @click="update(report, 'resolve')">Resolved</button>
          <button class="btn btn-sm btn-ghost" @click="update(report, 'dismiss')">Dismiss</button>
        </div>
      </article>
    </div>
    <PaginationBar :page="data.page" :pages="data.pages" @change="(p) => { page = p; load() }" />

    <ModalDialog v-if="removeTarget" title="Remove listing" @close="removeTarget = null">
      <p class="small muted">{{ removeTarget.listing.title }}</p>
      <div class="form-group">
        <label for="rm-reason">Reason (sent to the seller)</label>
        <textarea id="rm-reason" v-model="reason" class="input" rows="3" maxlength="500"></textarea>
      </div>
      <template #footer>
        <button class="btn" @click="removeTarget = null">Cancel</button>
        <button class="btn btn-danger" :disabled="working || reason.trim().length < 5" @click="removeListing">Remove</button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 10px; }
.report { display: grid; grid-template-columns: 300px 1fr auto; gap: 16px; padding: 14px; align-items: center; }
.listing { display: flex; gap: 10px; align-items: center; color: var(--text); text-decoration: none !important; min-width: 0; }
.min0 { min-width: 0; display: flex; flex-direction: column; }
.actions { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
@media (max-width: 860px) {
  .report { grid-template-columns: 1fr; }
  .actions { justify-content: flex-start; }
}
</style>
