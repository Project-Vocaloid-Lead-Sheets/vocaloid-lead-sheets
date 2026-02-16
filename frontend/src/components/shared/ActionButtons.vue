<template>
  <div class="d-flex gap-2">
    <button
      type="button"
      :class="hasActiveFilters ? 'btn btn-sm btn-light' : 'btn btn-sm btn-outline-light'"
      data-bs-toggle="modal"
      :data-bs-target="filterModalId"
    >
      <i class="bi bi-filter"></i>
    </button>
    <button class="btn btn-sm btn-outline-light" @click="emit('shuffle')">
      <i class="bi bi-shuffle"></i>
    </button>
    <button
      class="btn btn-sm btn-outline-light"
      :data-bs-target="areGroupsCollapsed ? '.song.collapse.show' : '.song.collapse'"
      data-bs-toggle="collapse"
      @click="emit('toggleCollapse')"
    >
      <i class="bi bi-chevron-expand"></i>
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  hasActiveFilters: boolean
  areGroupsCollapsed: boolean
  filterModalId: string
}

defineProps<Props>()

const emit = defineEmits<{
  shuffle: []
  toggleCollapse: []
}>()
</script>
