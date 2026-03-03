<template>
  <div class="d-flex flex-column gap-2">
    <ActiveFiltersBanner
      v-if="showActiveFilters"
      :selected-labels="selectedLabels"
      :selected-producers="selectedProducers"
      :selected-singers="selectedSingers"
      :date-range="dateRange"
      :length-range="lengthRange"
    />

    <InstrumentButtons
      :instruments="instruments"
      v-model:selected-instrument="selectedInstrument"
    />

    <div class="d-flex">
      <SearchBar
        v-model:search-query="searchQuery"
        @reset="emit('reset')"
        class="me-2 flex-grow-1"
      />
      <ActionButtons
        :has-active-filters="hasActiveFilters"
        :are-groups-collapsed="areGroupsCollapsed"
        :filter-modal-id="filterModalId"
        @shuffle="emit('shuffle')"
        @toggle-collapse="emit('toggleCollapse')"
      />
    </div>

    <GroupSortControls v-model:group-by="groupBy" v-model:sort-by="sortBy" />
  </div>
</template>

<script setup lang="ts">
import type { Instrument } from '@/types/types'
import InstrumentButtons from '@/components/shared/InstrumentButtons.vue'
import SearchBar from '@/components/shared/SearchBar.vue'
import ActionButtons from '@/components/shared/ActionButtons.vue'
import GroupSortControls from '@/components/shared/GroupSortControls.vue'
import ActiveFiltersBanner from '@/components/shared/ActiveFiltersBanner.vue'

interface Props {
  instruments: Instrument[]
  hasActiveFilters: boolean
  areGroupsCollapsed: boolean
  filterModalId: string
  showActiveFilters?: boolean
  selectedLabels?: string[]
  selectedProducers?: string[]
  selectedSingers?: string[]
  dateRange?: { start: string; end: string }
  lengthRange?: { min: number | null; max: number | null }
}

withDefaults(defineProps<Props>(), {
  showActiveFilters: false,
  selectedLabels: () => [],
  selectedProducers: () => [],
  selectedSingers: () => [],
  dateRange: () => ({ start: '', end: '' }),
  lengthRange: () => ({ min: null, max: null }),
})

const selectedInstrument = defineModel<Instrument>('selectedInstrument', { required: true })
const searchQuery = defineModel<string>('searchQuery', { required: true })
const groupBy = defineModel<string>('groupBy', { required: true })
const sortBy = defineModel<string>('sortBy', { required: true })

const emit = defineEmits<{
  reset: []
  shuffle: []
  toggleCollapse: []
}>()
</script>
