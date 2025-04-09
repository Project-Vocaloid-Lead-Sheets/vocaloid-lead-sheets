<script setup lang="ts">
import Sidebar from '@/components/Sidebar.vue'
</script>

<template>
  <main class="container-fluid min-vh-100 d-flex flex-column">
    <div class="row flex-grow-1 bd-layout">
      <div class="col-auto p-0" style="max-width: 25%">
        <Sidebar />
      </div>
      <div class="col p-0">
        <RouterView />
      </div>
    </div>
  </main>
</template>
