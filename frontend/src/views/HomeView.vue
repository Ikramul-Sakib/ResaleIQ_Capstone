<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { errorMessage } from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import ListingCard from '@/components/ListingCard.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import { CONDITIONS, LOCATIONS } from '@/utils'

const route = useRoute()
const router = useRouter()

const categories = ref([])
const results = ref({ items: [], page: 1, pages: 0, total: 0 })
const loading = ref(true)
const error = ref('')
const showFilters = ref(false)

const filters = reactive({ category: '', min_price: '', max_price: '', condition: '', location: '', sort: 'newest' })

const query = computed(() => route.query)
const activeCategory = computed(() => categories.value.find((c) => c.slug === query.value.category))
const hasFilters = computed(() =>
  ['q', 'category', 'min_price', 'max_price', 'condition', 'location'].some((key) => query.value[key]),
)

function syncFiltersFromRoute() {
  for (const key of Object.keys(filters)) filters[key] = query.value[key] || (key === 'sort' ? 'newest' : '')
}

function pushQuery(changes) {
  const next = { ...query.value, ...changes }
  for (const key of Object.keys(next)) if (next[key] === '' || next[key] == null) delete next[key]
  if (next.sort === 'newest') delete next.sort
  if (!('page' in changes)) delete next.page
  router.push({ name: 'home', query: next })
}

function applyFilters() {
  pushQuery({ ...filters })
  showFilters.value = false
}

function clearFilters() {
  router.push({ name: 'home' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/listings', { params: { ...query.value, per_page: 12 } })
    results.value = data
  } catch (err) {
    error.value = errorMessage(err, 'Could not load listings.')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  syncFiltersFromRoute()
  load()
  try {
    categories.value = (await api.get('/categories')).data
  } catch {
    /* the page still works without the category list */
  }
})

watch(query, () => {
  syncFiltersFromRoute()
  load()
})
</script>

<template>
  <section v-if="!hasFilters" class="hero">
    <div class="container">
      <h1>Buy and sell pre-owned items across Bangladesh</h1>
      <p>Every listing is reviewed by our team. Get an AI price estimate before you sell.</p>
      <div class="row">
        <RouterLink to="/sell" class="btn btn-accent"><AppIcon name="plus" :size="18" /> Post a free ad</RouterLink>
        <a href="#listings" class="btn hero-btn">Browse items</a>
      </div>
    </div>
  </section>

  <div class="container page">
    <div class="chips" role="list">
      <button class="chip" :class="{ active: !query.category }" @click="pushQuery({ category: '' })">All</button>
      <button
        v-for="category in categories"
        :key="category.id"
        class="chip"
        :class="{ active: query.category === category.slug }"
        @click="pushQuery({ category: category.slug })"
      >
        {{ category.name }} <span class="muted tiny" v-if="category.listing_count">{{ category.listing_count }}</span>
      </button>
    </div>

    <div id="listings" class="layout">
      <aside class="filters card" :class="{ open: showFilters }">
        <div class="card-body">
          <div class="row between mb">
            <h3 style="margin: 0">Filters</h3>
            <button class="btn btn-ghost btn-sm mobile-only" @click="showFilters = false">Close</button>
          </div>
          <form @submit.prevent="applyFilters">
            <div class="form-group">
              <label for="f-category">Category</label>
              <select id="f-category" v-model="filters.category" class="input">
                <option value="">All categories</option>
                <option v-for="c in categories" :key="c.id" :value="c.slug">{{ c.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <span class="label">Price (৳)</span>
              <div class="row price-range">
                <input v-model="filters.min_price" class="input" type="number" min="0" placeholder="Min" aria-label="Minimum price" />
                <span class="muted">–</span>
                <input v-model="filters.max_price" class="input" type="number" min="0" placeholder="Max" aria-label="Maximum price" />
              </div>
            </div>
            <div class="form-group">
              <label for="f-condition">Condition</label>
              <select id="f-condition" v-model="filters.condition" class="input">
                <option value="">Any condition</option>
                <option v-for="c in CONDITIONS" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label for="f-location">Location</label>
              <input id="f-location" v-model="filters.location" class="input" list="bd-locations" placeholder="Any location" />
              <datalist id="bd-locations"><option v-for="l in LOCATIONS" :key="l" :value="l" /></datalist>
            </div>
            <button class="btn btn-primary btn-block" type="submit">Apply filters</button>
            <button v-if="hasFilters" class="btn btn-ghost btn-block mt" type="button" @click="clearFilters">Clear all</button>
          </form>
        </div>
      </aside>

      <section class="results">
        <div class="results-head">
          <div>
            <h2 style="margin: 0">
              <template v-if="query.q">Results for “{{ query.q }}”</template>
              <template v-else-if="activeCategory">{{ activeCategory.name }}</template>
              <template v-else>Latest listings</template>
            </h2>
            <span class="muted small">{{ results.total }} item{{ results.total === 1 ? '' : 's' }}</span>
          </div>
          <div class="row">
            <button class="btn btn-sm mobile-only" @click="showFilters = true"><AppIcon name="filter" :size="16" /> Filters</button>
            <select v-model="filters.sort" class="input sort" aria-label="Sort by" @change="pushQuery({ sort: filters.sort })">
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="price_asc">Price: low to high</option>
              <option value="price_desc">Price: high to low</option>
            </select>
          </div>
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="loading" class="spinner"></div>
        <div v-else-if="!results.items.length" class="empty card">
          <h3>No items found</h3>
          <p>Try a different search or remove some filters.</p>
          <button v-if="hasFilters" class="btn" @click="clearFilters">Clear filters</button>
        </div>
        <div v-else class="listing-grid">
          <ListingCard v-for="listing in results.items" :key="listing.id" :listing="listing" />
        </div>
        <PaginationBar :page="results.page" :pages="results.pages" @change="(p) => pushQuery({ page: p })" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.hero { background: linear-gradient(135deg, #0f766e 0%, #115e59 60%, #134e4a 100%); color: #fff; padding: 40px 0; }
.hero h1 { font-size: 2rem; max-width: 640px; }
.hero p { opacity: 0.9; max-width: 560px; margin-bottom: 20px; }
.hero-btn { background: rgba(255, 255, 255, 0.12); color: #fff; border-color: rgba(255, 255, 255, 0.35); }
.hero-btn:hover { background: rgba(255, 255, 255, 0.2); }
.chips { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 18px; }
.layout { display: grid; grid-template-columns: 250px 1fr; gap: 20px; align-items: start; }
.filters { position: sticky; top: 80px; }
.price-range { flex-wrap: nowrap; }
.results-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.sort { width: auto; }
.mobile-only { display: none; }
@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  .filters { display: none; position: fixed; inset: 0; z-index: 90; border-radius: 0; overflow-y: auto; }
  .filters.open { display: block; }
  .mobile-only { display: inline-flex; }
  .hero h1 { font-size: 1.5rem; }
}
</style>
