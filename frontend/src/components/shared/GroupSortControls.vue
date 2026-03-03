<template>
  <div class="d-flex flex-nowrap gap-2 align-items-center w-100">
    <div class="input-group sort-control">
      <button
        type="button"
        class="input-group-text sort-icon-btn group-toggle-btn"
        :aria-label="groupToggleLabel"
        :title="groupToggleLabel"
        @click="emit('toggleCollapse')"
      >
        <i :class="groupToggleIcon"></i>
      </button>
      <select :id="props.groupSelectId" class="form-select form-select-sm" v-model="groupBy">
        <option value="none">None</option>
        <option value="singer">Singer</option>
        <option value="producer">Producer</option>
      </select>
    </div>
    <div class="input-group sort-control">
      <button
        type="button"
        class="input-group-text sort-icon-btn sort-direction-btn"
        :aria-label="sortDirectionLabel"
        :title="sortDirectionLabel"
        @click="toggleSortDirection"
      >
        <i :class="sortDirectionIcon"></i>
      </button>
      <select
        :id="props.sortSelectId"
        class="form-select form-select-sm"
        :value="currentSortField"
        @change="onSortFieldChange"
      >
        <option value="title">Title</option>
        <option value="bpm">BPM</option>
        <option value="length">Length</option>
        <option value="tv-length">TV Size Length</option>
        <option value="date">Release Date</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  groupSelectId?: string
  sortSelectId?: string
  areGroupsCollapsed: boolean
}

const props = withDefaults(defineProps<Props>(), {
  groupSelectId: 'group-select',
  sortSelectId: 'sort-select',
})

const emit = defineEmits<{
  toggleCollapse: []
}>()

const groupBy = defineModel<string>('groupBy', { required: true })
const sortBy = defineModel<string>('sortBy', { required: true })

type SortField = 'title' | 'bpm' | 'length' | 'tv-length' | 'date'
type SortOrder = 'asc' | 'desc'

const sortFields = new Set<SortField>(['title', 'bpm', 'length', 'tv-length', 'date'])
const sortOrders = new Set<SortOrder>(['asc', 'desc'])

const parseSortBy = (value: string): { field: SortField; order: SortOrder } => {
  const lastDashIndex = value.lastIndexOf('-')
  if (lastDashIndex === -1) {
    return { field: 'title', order: 'asc' }
  }

  const fieldCandidate = value.slice(0, lastDashIndex) as SortField
  const orderCandidate = value.slice(lastDashIndex + 1) as SortOrder

  if (!sortFields.has(fieldCandidate) || !sortOrders.has(orderCandidate)) {
    return { field: 'title', order: 'asc' }
  }

  return { field: fieldCandidate, order: orderCandidate }
}

const currentSortState = computed(() => parseSortBy(sortBy.value))

const currentSortField = computed(() => currentSortState.value.field)

const currentSortOrder = computed(() => currentSortState.value.order)

const groupToggleIcon = computed(() =>
  props.areGroupsCollapsed ? 'bi bi-folder small' : 'bi bi-folder2-open small',
)

const groupToggleLabel = computed(() =>
  props.areGroupsCollapsed
    ? 'Groups collapsed (click to expand all)'
    : 'Groups expanded (click to collapse all)',
)

const sortDirectionIcon = computed(() => {
  const isTitleSort = currentSortField.value === 'title'

  if (isTitleSort) {
    return currentSortOrder.value === 'asc'
      ? 'bi bi-sort-alpha-down small'
      : 'bi bi-sort-alpha-up small'
  }

  return currentSortOrder.value === 'asc'
    ? 'bi bi-sort-numeric-down small'
    : 'bi bi-sort-numeric-up small'
})

const sortDirectionLabel = computed(() =>
  currentSortOrder.value === 'asc'
    ? 'Sort ascending (click to reverse)'
    : 'Sort descending (click to reverse)',
)

const onSortFieldChange = (event: Event) => {
  const nextField = (event.target as HTMLSelectElement).value as SortField
  const field = sortFields.has(nextField) ? nextField : 'title'
  sortBy.value = `${field}-${currentSortOrder.value}`
}

const toggleSortDirection = () => {
  const nextOrder = currentSortOrder.value === 'asc' ? 'desc' : 'asc'
  sortBy.value = `${currentSortField.value}-${nextOrder}`
}
</script>

<style scoped>
.sort-control {
  flex: 1 1 50%;
  min-width: 0;
}

.sort-icon-btn {
  background-color: transparent;
  color: rgba(255, 255, 255, 0.9);
  border-color: rgba(255, 255, 255, 0.5);
}

.sort-icon-btn i {
  color: inherit;
}

.sort-direction-btn {
  cursor: pointer;
}

.group-toggle-btn {
  cursor: pointer;
}

.sort-direction-btn:hover,
.group-toggle-btn:hover,
.sort-direction-btn:focus-visible,
.group-toggle-btn:focus-visible {
  background-color: rgba(255, 255, 255, 0.9);
  color: #206071;
}
</style>
