import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
  { path: '/listings/:id', name: 'listing', component: () => import('@/views/ListingDetailView.vue') },
  { path: '/sellers/:id', name: 'seller', component: () => import('@/views/SellerProfileView.vue') },

  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guest: true } },
  { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { guest: true } },
  { path: '/forgot-password', name: 'forgot', component: () => import('@/views/ForgotPasswordView.vue'), meta: { guest: true } },
  { path: '/reset-password', name: 'reset', component: () => import('@/views/ResetPasswordView.vue') },

  { path: '/sell', name: 'sell', component: () => import('@/views/ListingFormView.vue'), meta: { auth: true } },
  { path: '/listings/:id/edit', name: 'edit-listing', component: () => import('@/views/ListingFormView.vue'), meta: { auth: true } },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { auth: true } },
  { path: '/wishlist', name: 'wishlist', component: () => import('@/views/WishlistView.vue'), meta: { auth: true } },
  { path: '/messages/:id?', name: 'messages', component: () => import('@/views/MessagesView.vue'), meta: { auth: true } },
  { path: '/cart', name: 'cart', component: () => import('@/views/CartView.vue'), meta: { auth: true } },
  { path: '/orders', name: 'orders', component: () => import('@/views/OrdersView.vue'), meta: { auth: true } },
  { path: '/orders/:id', name: 'order', component: () => import('@/views/OrderDetailView.vue'), meta: { auth: true } },
  { path: '/notifications', name: 'notifications', component: () => import('@/views/NotificationsView.vue'), meta: { auth: true } },
  { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { auth: true } },

  { path: '/admin', name: 'admin', component: () => import('@/views/admin/AdminDashboardView.vue'), meta: { admin: true } },
  { path: '/admin/listings', name: 'admin-listings', component: () => import('@/views/admin/AdminListingsView.vue'), meta: { admin: true } },
  { path: '/admin/orders', name: 'admin-orders', component: () => import('@/views/admin/AdminOrdersView.vue'), meta: { admin: true } },
  { path: '/admin/reports', name: 'admin-reports', component: () => import('@/views/admin/AdminReportsView.vue'), meta: { admin: true } },
  { path: '/admin/users', name: 'admin-users', component: () => import('@/views/admin/AdminUsersView.vue'), meta: { admin: true } },
  { path: '/admin/categories', name: 'admin-categories', component: () => import('@/views/admin/AdminCategoriesView.vue'), meta: { admin: true } },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.path === from.path) return false // only the query changed (filters, pages)
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()
  if ((to.meta.auth || to.meta.admin) && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.admin && !auth.isAdmin) return { name: 'home' }
  if (to.meta.guest && auth.isLoggedIn) return { name: 'home' }
  return true
})

export default router
