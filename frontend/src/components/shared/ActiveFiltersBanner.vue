<template>
  <div v-if="hasFilters" class="mb-2 p-2 bg-white text-dark rounded small border">
    <strong>Active Filters:</strong>
    <div v-if="selectedLabels.length > 0">Labels: {{ selectedLabels.join(', ') }}</div>
    <div v-if="selectedProducers.length > 0">Producers: {{ selectedProducers.join(', ') }}</div>
    <div v-if="selectedSingers.length > 0">Singers: {{ selectedSingers.join(', ') }}</div>
    <div v-if="includedKeys.length > 0">Included keys: {{ includedKeys.join(', ') }}</div>
    <div v-if="excludedKeys.length > 0">Excluded keys: {{ excludedKeys.join(', ') }}</div>
    <template v-for="criterion in difficultyCriteria" :key="criterion">
      <div v-if="isRangeActive(difficultyRanges[criterion])">
        {{ difficultyLabels[criterion] }} difficulty: {{ difficultyRanges[criterion].min ?? 1 }} to
        {{ difficultyRanges[criterion].max ?? 'any' }}
      </div>
    </template>
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
import { difficultyCriteria } from '@/types/types'
import type { DifficultyRanges } from '@/types/types'
import { createDifficultyRanges, difficultyLabels, isRangeActive } from '@/utils/songMetadata'

interface Props {
  selectedLabels: string[]
  selectedProducers: string[]
  selectedSingers: string[]
  includedKeys?: string[]
  excludedKeys?: string[]
  difficultyRanges?: DifficultyRanges
  dateRange: { start: string; end: string }
  lengthRange: { min: number | null; max: number | null }
}

const props = withDefaults(defineProps<Props>(), {
  includedKeys: () => [],
  excludedKeys: () => [],
  difficultyRanges: createDifficultyRanges,
})

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
    props.includedKeys.length > 0 ||
    props.excludedKeys.length > 0 ||
    difficultyCriteria.some((criterion) => isRangeActive(props.difficultyRanges[criterion])) ||
    props.dateRange.start !== '' ||
    props.dateRange.end !== '' ||
    props.lengthRange.min !== null ||
    props.lengthRange.max !== null
  )
})
</script>
