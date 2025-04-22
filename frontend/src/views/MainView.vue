<script setup lang="ts">
import Sidebar from '@/components/Sidebar.vue'
import Navbar from '@/components/Navbar.vue'
</script>

<template>
  <main class="container-fluid min-vh-100 d-flex flex-column">
    <div class="row flex-grow-1 bd-layout">
      <!-- Desktop Sidebar -->
      <div class="col-auto p-0 d-none d-lg-block" style="max-width: 25%">
        <Sidebar />
      </div>
      <!-- Mobile Navbar -->
      <div class="col-12 d-block d-lg-none">
        <Navbar />
      </div>
      <div class="col p-0">
        <RouterView />
      </div>
    </div>
  </main>
</template>
