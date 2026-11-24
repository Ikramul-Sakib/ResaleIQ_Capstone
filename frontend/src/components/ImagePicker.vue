<script setup>
import { computed, onUnmounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import { imageUrl } from '@/api'
import { compressImage } from '@/utils'

const MAX = 6
const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']

// existing: [{ id, url }] already saved on the server; files: new File objects
const existing = defineModel('existing', { type: Array, default: () => [] })
const files = defineModel('files', { type: Array, default: () => [] })
defineProps({ error: { type: String, default: '' } })

const input = ref(null)
const problem = ref('')
const processing = ref(false)
const previews = new Map()

const count = computed(() => existing.value.length + files.value.length)

function previewFor(file) {
  if (!previews.has(file)) previews.set(file, URL.createObjectURL(file))
  return previews.get(file)
}

async function addFiles(list) {
  problem.value = ''
  const incoming = Array.from(list || [])
  const accepted = []
  for (const file of incoming) {
    if (!ALLOWED.includes(file.type)) {
      problem.value = `${file.name} is not a JPG, PNG or WebP image.`
      continue
    }
    if (count.value + accepted.length >= MAX) {
      problem.value = `You can add up to ${MAX} photos.`
      break
    }
    accepted.push(file)
  }
  processing.value = true
  const compressed = await Promise.all(accepted.map((file) => compressImage(file)))
  processing.value = false
  const tooBig = compressed.filter((file) => file.size > 8 * 1024 * 1024)
  if (tooBig.length) problem.value = `${tooBig[0].name} is larger than 8 MB.`
  files.value = [...files.value, ...compressed.filter((file) => file.size <= 8 * 1024 * 1024)]
  if (input.value) input.value.value = ''
}

function removeExisting(index) {
  existing.value = existing.value.filter((_, i) => i !== index)
}

function removeFile(index) {
  const file = files.value[index]
  if (previews.has(file)) {
    URL.revokeObjectURL(previews.get(file))
    previews.delete(file)
  }
  files.value = files.value.filter((_, i) => i !== index)
}

function onDrop(event) {
  addFiles(event.dataTransfer?.files)
}

onUnmounted(() => previews.forEach((url) => URL.revokeObjectURL(url)))
</script>

<template>
  <div>
    <div class="picker" :class="{ invalid: error }">
      <div v-for="(image, index) in existing" :key="`e${image.id}`" class="tile">
        <img :src="imageUrl(image.url)" alt="" />
        <span v-if="index === 0" class="cover">Cover</span>
        <button type="button" class="remove" aria-label="Remove photo" @click="removeExisting(index)"><AppIcon name="close" :size="14" /></button>
      </div>
      <div v-for="(file, index) in files" :key="`f${index}${file.name}`" class="tile">
        <img :src="previewFor(file)" alt="" />
        <span v-if="!existing.length && index === 0" class="cover">Cover</span>
        <button type="button" class="remove" aria-label="Remove photo" @click="removeFile(index)"><AppIcon name="close" :size="14" /></button>
      </div>
      <button
        v-if="count < MAX"
        type="button"
        class="tile add"
        :disabled="processing"
        @click="input?.click()"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <AppIcon name="image" :size="26" />
        <span>{{ processing ? 'Preparing…' : 'Add photos' }}</span>
        <span class="tiny muted">{{ count }}/{{ MAX }}</span>
      </button>
    </div>
    <input ref="input" type="file" accept="image/jpeg,image/png,image/webp" multiple hidden @change="addFiles($event.target.files)" />
    <div v-if="problem || error" class="field-error">{{ problem || error }}</div>
    <div v-else class="hint">Up to 6 photos (JPG, PNG or WebP). The first photo is the cover. Large photos are resized automatically.</div>
  </div>
</template>

<style scoped>
.picker { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 10px; }
.tile { position: relative; aspect-ratio: 1; border-radius: 10px; overflow: hidden; background: #eef1f4; border: 1px solid var(--border); }
.tile img { width: 100%; height: 100%; object-fit: cover; }
.cover { position: absolute; left: 6px; bottom: 6px; background: rgba(15, 23, 42, 0.75); color: #fff; font-size: 0.7rem; padding: 2px 7px; border-radius: 6px; }
.remove { position: absolute; right: 6px; top: 6px; width: 26px; height: 26px; border-radius: 999px; border: none; background: rgba(255, 255, 255, 0.92); display: grid; place-items: center; cursor: pointer; }
.add { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; border: 2px dashed #c3ccd6; background: #fafbfc; color: var(--muted); cursor: pointer; font: inherit; font-size: 0.85rem; font-weight: 600; }
.add:hover { border-color: var(--primary); color: var(--primary); }
.invalid .add { border-color: var(--danger); }
</style>
