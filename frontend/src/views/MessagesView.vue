<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { errorMessage, imageUrl } from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { formatPrice, timeAgo } from '@/utils'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

const conversations = ref([])
const thread = ref(null)
const messages = ref([])
const loadingList = ref(true)
const loadingThread = ref(false)
const draft = ref('')
const sending = ref(false)
const scroller = ref(null)
let timer = null

const activeId = computed(() => (route.params.id ? Number(route.params.id) : null))

async function loadList() {
  try {
    conversations.value = (await api.get('/conversations')).data.items
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    loadingList.value = false
  }
}

async function loadThread(showSpinner = true) {
  if (!activeId.value) {
    thread.value = null
    return
  }
  if (showSpinner) loadingThread.value = true
  try {
    const { data } = await api.get(`/conversations/${activeId.value}`)
    const grew = data.messages.length !== messages.value.length
    thread.value = data.conversation
    messages.value = data.messages
    const item = conversations.value.find((c) => c.id === activeId.value)
    if (item) item.unread_count = 0
    if (grew) scrollToBottom()
    auth.refreshSummary()
  } catch (err) {
    if (err.response?.status === 404) router.replace('/messages')
    else toast.error(errorMessage(err))
  } finally {
    loadingThread.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function send() {
  const body = draft.value.trim()
  if (!body) return
  sending.value = true
  try {
    const { data } = await api.post(`/conversations/${activeId.value}/messages`, { body })
    messages.value.push(data)
    draft.value = ''
    scrollToBottom()
    loadList()
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    sending.value = false
  }
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

watch(activeId, () => {
  messages.value = []
  loadThread()
})

onMounted(async () => {
  await loadList()
  loadThread()
  // Simple polling keeps the chat up to date without WebSockets.
  timer = setInterval(() => {
    loadList()
    if (activeId.value) loadThread(false)
  }, 8000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="container page">
    <h1>Messages</h1>
    <div class="inbox card" :class="{ 'has-thread': activeId }">
      <aside class="list">
        <div v-if="loadingList" class="spinner"></div>
        <div v-else-if="!conversations.length" class="empty small">
          <p>No conversations yet.</p>
          <p>Find an item you like and message the seller.</p>
        </div>
        <RouterLink
          v-for="c in conversations"
          :key="c.id"
          :to="`/messages/${c.id}`"
          class="conv"
          :class="{ active: c.id === activeId }"
        >
          <img class="thumb" :src="imageUrl(c.listing.image)" alt="" />
          <div class="conv-text">
            <div class="row between">
              <strong class="truncate">{{ c.other_user.name }}</strong>
              <span class="tiny muted">{{ timeAgo(c.updated_at) }}</span>
            </div>
            <div class="tiny truncate">{{ c.listing.title }}</div>
            <div class="tiny muted truncate">
              <template v-if="c.last_message">{{ c.last_message.sender_id === auth.user.id ? 'You: ' : '' }}{{ c.last_message.body }}</template>
            </div>
          </div>
          <span v-if="c.unread_count" class="unread">{{ c.unread_count }}</span>
        </RouterLink>
      </aside>

      <section class="thread">
        <div v-if="!activeId" class="empty">
          <AppIcon name="chat" :size="36" />
          <p>Select a conversation to read it.</p>
        </div>
        <div v-else-if="loadingThread && !thread" class="spinner"></div>
        <template v-else-if="thread">
          <header class="thread-head">
            <RouterLink to="/messages" class="btn btn-ghost btn-icon back" aria-label="Back to conversations"><AppIcon name="arrowLeft" /></RouterLink>
            <RouterLink :to="`/listings/${thread.listing.id}`" class="thread-listing">
              <img class="thumb" :src="imageUrl(thread.listing.image)" alt="" />
              <div class="conv-text">
                <strong class="truncate">{{ thread.listing.title }}</strong>
                <span class="tiny muted">{{ formatPrice(thread.listing.price) }} · {{ thread.role === 'buyer' ? 'Seller' : 'Buyer' }}: {{ thread.other_user.name }}</span>
              </div>
            </RouterLink>
            <StatusBadge v-if="thread.listing.status !== 'approved'" :status="thread.listing.status" />
          </header>
          <div ref="scroller" class="messages">
            <div v-for="m in messages" :key="m.id" class="bubble" :class="{ mine: m.sender_id === auth.user.id }">
              <div>{{ m.body }}</div>
              <div class="time">{{ timeAgo(m.created_at) }}</div>
            </div>
          </div>
          <form v-if="thread.listing.status !== 'removed'" class="composer" @submit.prevent="send">
            <textarea v-model="draft" class="input" rows="1" maxlength="2000" placeholder="Write a message…" @keydown="onKeydown"></textarea>
            <button class="btn btn-primary" :disabled="sending || !draft.trim()" aria-label="Send"><AppIcon name="send" :size="18" /></button>
          </form>
          <div v-else class="alert alert-warning" style="margin: 12px">This listing was removed, so the conversation is closed.</div>
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.inbox { display: grid; grid-template-columns: 320px 1fr; height: min(70vh, 680px); min-height: 420px; overflow: hidden; margin-top: 12px; }
.list { border-right: 1px solid var(--border); overflow-y: auto; }
.conv { display: flex; gap: 10px; align-items: center; padding: 12px 14px; border-bottom: 1px solid var(--border); color: var(--text); text-decoration: none !important; position: relative; }
.conv:hover { background: #f7f9fa; }
.conv.active { background: var(--primary-soft); }
.conv-text { min-width: 0; flex: 1; display: flex; flex-direction: column; }
.unread { background: var(--primary); color: #fff; border-radius: 999px; font-size: 0.72rem; font-weight: 700; min-width: 20px; height: 20px; display: grid; place-items: center; padding: 0 6px; }
.thread { display: flex; flex-direction: column; min-width: 0; }
.thread .empty { margin: auto; }
.thread-head { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid var(--border); }
.thread-listing { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; color: var(--text); text-decoration: none !important; }
.back { display: none; }
.messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; background: #fafbfc; }
.bubble { max-width: 75%; padding: 9px 13px; border-radius: 14px 14px 14px 4px; background: #fff; border: 1px solid var(--border); white-space: pre-wrap; word-wrap: break-word; }
.bubble.mine { align-self: flex-end; background: var(--primary); color: #fff; border-color: var(--primary); border-radius: 14px 14px 4px 14px; }
.time { font-size: 0.7rem; opacity: 0.7; margin-top: 2px; }
.composer { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border); }
.composer textarea { min-height: 42px; max-height: 120px; resize: none; }
@media (max-width: 760px) {
  .inbox { grid-template-columns: 1fr; height: calc(100vh - 190px); }
  .inbox.has-thread .list { display: none; }
  .inbox:not(.has-thread) .thread { display: none; }
  .back { display: inline-flex; }
  .list { border-right: none; }
}
</style>
