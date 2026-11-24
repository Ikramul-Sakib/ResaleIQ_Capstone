<template>
  <div class="admin-head">
    <h1>Admin panel</h1>
    <nav class="tabs">
      <RouterLink to="/admin" class="tab" exact-active-class="active">Overview</RouterLink>
      <RouterLink to="/admin/listings" class="tab" active-class="active">Listings</RouterLink>
      <RouterLink to="/admin/orders" class="tab" active-class="active">Orders</RouterLink>
      <RouterLink to="/admin/reports" class="tab" active-class="active">Reports</RouterLink>
      <RouterLink to="/admin/users" class="tab" active-class="active">Users</RouterLink>
      <RouterLink to="/admin/categories" class="tab" active-class="active">Categories</RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.admin-head h1 { margin-bottom: 12px; }
.tab { text-decoration: none !important; }
</style>
