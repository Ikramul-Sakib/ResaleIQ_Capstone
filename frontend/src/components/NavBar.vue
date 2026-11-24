<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const search = ref(route.query.q || '')
const menuOpen = ref(false)

watch(() => route.fullPath, () => {
  menuOpen.value = false
  if (route.name === 'home') search.value = route.query.q || ''
})

function submitSearch() {
  const q = search.value.trim()
  router.push({ name: 'home', query: q ? { q } : {} })
}

function logout() {
  auth.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <header class="nav">
    <div class="container nav-inner">
      <RouterLink to="/" class="brand" aria-label="ResaleIQ home">
        <span class="logo">R</span>
        <span>Resale<strong>IQ</strong></span>
      </RouterLink>

      <form class="search" role="search" @submit.prevent="submitSearch">
        <AppIcon name="search" :size="18" class="search-icon" />
        <input v-model="search" type="search" placeholder="Search phones, laptops, furniture…" aria-label="Search listings" />
      </form>

      <nav class="actions">
        <RouterLink to="/sell" class="btn btn-accent sell-btn">
          <AppIcon name="plus" :size="18" /> <span>Sell</span>
        </RouterLink>

        <template v-if="auth.isLoggedIn">
          <RouterLink to="/wishlist" class="icon-link" title="Wishlist" aria-label="Wishlist">
            <AppIcon name="heart" />
          </RouterLink>
          <RouterLink to="/cart" class="icon-link" title="Cart" aria-label="Cart">
            <AppIcon name="cart" />
            <span v-if="auth.cartCount" class="dot dot-cart">{{ auth.cartCount }}</span>
          </RouterLink>
          <RouterLink to="/messages" class="icon-link" title="Messages" aria-label="Messages">
            <AppIcon name="chat" />
            <span v-if="auth.unreadMessages" class="dot">{{ auth.unreadMessages > 9 ? '9+' : auth.unreadMessages }}</span>
          </RouterLink>
          <RouterLink to="/notifications" class="icon-link" title="Notifications" aria-label="Notifications">
            <AppIcon name="bell" />
            <span v-if="auth.unreadNotifications" class="dot">{{ auth.unreadNotifications > 9 ? '9+' : auth.unreadNotifications }}</span>
          </RouterLink>
          <div class="user-menu">
            <button class="icon-link avatar" :aria-expanded="menuOpen" aria-label="Account menu" @click="menuOpen = !menuOpen">
              {{ auth.user.name.charAt(0).toUpperCase() }}
            </button>
            <div v-if="menuOpen" class="dropdown card" @click.stop>
              <div class="dropdown-head">
                <div class="bold truncate">{{ auth.user.name }}</div>
                <div class="tiny muted truncate">{{ auth.user.email }}</div>
              </div>
              <RouterLink to="/dashboard"><AppIcon name="grid" :size="16" /> My listings</RouterLink>
              <RouterLink to="/orders?tab=purchases"><AppIcon name="receipt" :size="16" /> My orders</RouterLink>
              <RouterLink to="/orders?tab=sales"><AppIcon name="package" :size="16" /> Sales
                <span v-if="auth.pendingSales" class="menu-count">{{ auth.pendingSales }}</span></RouterLink>
              <RouterLink to="/messages"><AppIcon name="chat" :size="16" /> Messages</RouterLink>
              <RouterLink to="/wishlist"><AppIcon name="heart" :size="16" /> Wishlist</RouterLink>
              <RouterLink to="/profile"><AppIcon name="user" :size="16" /> Profile</RouterLink>
              <RouterLink v-if="auth.isAdmin" to="/admin"><AppIcon name="shield" :size="16" /> Admin panel</RouterLink>
              <button @click="logout"><AppIcon name="logout" :size="16" /> Log out</button>
            </div>
          </div>
        </template>
        <template v-else>
          <RouterLink to="/login" class="btn btn-ghost">Log in</RouterLink>
          <RouterLink to="/register" class="btn btn-primary hide-sm">Sign up</RouterLink>
        </template>
      </nav>
    </div>
    <div v-if="menuOpen" class="backdrop" @click="menuOpen = false"></div>
  </header>
</template>

<style scoped>
.nav { background: #fff; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 50; }
.nav-inner { display: flex; align-items: center; gap: 16px; height: 64px; }
.brand { display: flex; align-items: center; gap: 8px; font-size: 1.2rem; color: var(--text); text-decoration: none !important; flex-shrink: 0; }
.brand strong { color: var(--primary); }
.logo { width: 32px; height: 32px; border-radius: 8px; background: var(--primary); color: #fff; display: grid; place-items: center; font-weight: 800; }
.search { flex: 1; position: relative; max-width: 520px; }
.search input { width: 100%; padding: 9px 12px 9px 38px; border: 1px solid #cfd6de; border-radius: 999px; font: inherit; background: var(--bg); }
.search input:focus { outline: 2px solid rgba(15, 118, 110, 0.25); border-color: var(--primary); background: #fff; }
.search-icon { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.actions { display: flex; align-items: center; gap: 6px; margin-left: auto; }
.icon-link { position: relative; display: grid; place-items: center; width: 40px; height: 40px; border-radius: 999px; color: var(--text); background: none; border: none; cursor: pointer; }
.icon-link:hover { background: #f2f4f7; text-decoration: none; }
.icon-link.router-link-active { color: var(--primary); }
.dot { position: absolute; top: 3px; right: 1px; min-width: 18px; height: 18px; padding: 0 4px; border-radius: 999px; background: var(--danger); color: #fff; font-size: 0.68rem; font-weight: 700; display: grid; place-items: center; }
.dot-cart { background: var(--primary); }
.menu-count { margin-left: auto; background: var(--accent); color: #1f1300; border-radius: 999px; font-size: 0.72rem; font-weight: 700; padding: 1px 7px; }
.avatar { background: var(--primary-soft); color: var(--primary-dark); font-weight: 700; }
.user-menu { position: relative; }
.dropdown { position: absolute; right: 0; top: 48px; width: 230px; padding: 6px; z-index: 60; box-shadow: var(--shadow-lg); }
.dropdown-head { padding: 8px 10px 10px; border-bottom: 1px solid var(--border); margin-bottom: 4px; }
.dropdown a, .dropdown button { display: flex; align-items: center; gap: 10px; width: 100%; padding: 9px 10px; border-radius: 6px; color: var(--text); background: none; border: none; font: inherit; font-size: 0.92rem; cursor: pointer; text-align: left; }
.dropdown a:hover, .dropdown button:hover { background: #f2f4f7; text-decoration: none; }
.backdrop { position: fixed; inset: 0; z-index: 40; }
@media (max-width: 720px) {
  .nav-inner { flex-wrap: wrap; height: auto; padding-top: 10px; padding-bottom: 10px; gap: 10px; }
  .search { order: 3; flex-basis: 100%; max-width: none; }
  .sell-btn span, .hide-sm { display: none; }
  .sell-btn { padding: 8px 10px; }
}
</style>
