<template>
  <div v-if="hasFilters" class="mb-2 p-2 bg-white text-dark rounded small border">
    <strong>Active Filters:</strong>
    <div v-if="selectedLabels.length > 0">Labels: {{ selectedLabels.join(', ') }}</div>
    <div v-if="selectedProducers.length > 0">Producers: {{ selectedProducers.join(', ') }}</div>
    <div v-if="selectedSingers.length > 0">Singers: {{ selectedSingers.join(', ') }}</div>
    <div v-if="dateRange.start || dateRange.end">
      Date: {{ dateRange.start || '...' }} to {{ dateRange.end || '...' }}
    </div>
    <div v-if="lengthRange.min !== null || lengthRange.max !== null">
      Length: {{ formatLength(lengthRange.min) || '...' }} to
      {{ formatLength(lengthRange.max) || '...' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  selectedLabels: string[]
  selectedProducers: string[]
  selectedSingers: string[]
  dateRange: { start: string; end: string }
  lengthRange: { min: number | null; max: number | null }
}

const props = defineProps<Props>()

const formatLength = (seconds: number | null): string => {
  if (seconds === null) return ''
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}

const hasFilters = computed(() => {
  return (
    props.selectedLabels.length > 0 ||
    props.selectedProducers.length > 0 ||
    props.selectedSingers.length > 0 ||
    props.dateRange.start !== '' ||
    props.dateRange.end !== '' ||
    props.lengthRange.min !== null ||
    props.lengthRange.max !== null
  )
})
</script>
