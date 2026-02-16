<style scoped>
/* Make the sidebar hamburger menu icon white */
.bi-list {
  color: #fff !important;
}
</style>
<script setup lang="ts">
/** The sidebar is for larger displays that can fit the song select list on the side.
 * Its counterpart is the navbar.*/

import { computed } from 'vue'
import { useSongFilters } from '@/scripts/useSongFilters'
import { useSongActions } from '@/scripts/useSongActions'
import { useSongsStore } from '@/stores/songs'
import FilterModal from '@/components/FilterModal.vue'
import DownloadModal from '@/components/DownloadModal.vue'
import InstrumentButtons from '@/components/shared/InstrumentButtons.vue'
import SearchBar from '@/components/shared/SearchBar.vue'
import ActionButtons from '@/components/shared/ActionButtons.vue'
import GroupSortControls from '@/components/shared/GroupSortControls.vue'
import ActiveFiltersBanner from '@/components/shared/ActiveFiltersBanner.vue'
import UnderReviewToggle from '@/components/shared/UnderReviewToggle.vue'
import SongActionButtons from '@/components/shared/SongActionButtons.vue'
import SongList from '@/components/shared/SongList.vue'

const songsStore = useSongsStore()

const {
  instruments,
  selectedInstrument,
  searchQuery,
  groupBy,
  sortBy,
  resetSearch,
  toggleGroupsCollapsed,
  areGroupsCollapsed,
  orderedSongs,
  pickRandomSong,
  selectedLabels,
  selectedProducers,
  selectedSingers,
  dateRange,
  toggleSidebarCollapsed,
  isSidebarCollapsed,
} = useSongFilters()

const { currentSong, currentInstrument, watchOnYouTube } = useSongActions()

// Computed property to check if any advanced filters are active and should be displayed
const hasActiveFilters = computed(() => {
  return (
    selectedLabels.value.length > 0 ||
    selectedProducers.value.length > 0 ||
    selectedSingers.value.length > 0 ||
    dateRange.value.start !== '' ||
    dateRange.value.end !== ''
  )
})
</script>

<template>
  <nav
    id="sidebar"
    class="text-light pt-2 px-3 d-flex flex-column"
    style="background-color: #206071; height: calc(var(--vh, 1vh) * 100)"
  >
    <!-- Sidebar Fixed Area -->
    <div class="d-flex flex-column mb-2">
      <!-- Sidebar Header -->
      <div class="d-flex flex-row mb-2">
        <a
          href="#"
          data-bs-target=".sidebar-nav-collapsible"
          data-bs-toggle="collapse"
          class="text-decoration-none"
          @click="toggleSidebarCollapsed"
          ><i class="bi bi-list"></i>
        </a>
        <span class="sidebar-nav-collapsible collapse collapse-horizontal ms-auto"
          ><RouterLink class="navbar-brand" to="/">Project VocaLead Sheets</RouterLink>
        </span>
      </div>
      <!-- Sidebar Body -->
      <div class="sidebar-nav-collapsible collapse collapse-horizontal">
        <!-- Active Filters Banner -->
        <ActiveFiltersBanner
          :selected-labels="selectedLabels"
          :selected-producers="selectedProducers"
          :selected-singers="selectedSingers"
          :date-range="dateRange"
        />

        <!-- Search Component -->
        <div class="d-flex flex-column gap-2">
          <!-- Row 1: Instrument/Transposition Buttons -->
          <InstrumentButtons
            :instruments="instruments"
            v-model:selected-instrument="selectedInstrument"
          />

          <!-- Row 2: Search Field + Navigation Buttons -->
          <div class="d-flex">
            <SearchBar v-model:search-query="searchQuery" @reset="resetSearch" class="me-2" />
            <ActionButtons
              :has-active-filters="hasActiveFilters"
              :are-groups-collapsed="areGroupsCollapsed"
              filter-modal-id="#filterModal"
              @shuffle="pickRandomSong"
              @toggle-collapse="toggleGroupsCollapsed"
            />
          </div>

          <!-- Row 3: Group + Sort Selects -->
          <GroupSortControls v-model:group-by="groupBy" v-model:sort-by="sortBy" />
        </div>
      </div>
    </div>
    <!-- Sidebar Scrollable Area -->
    <div
      id="sidebar-nav"
      class="sidebar-nav-collapsible collapse collapse-horizontal overflow-auto"
      style="flex: 1 1 0; min-height: 0"
    >
      <SongList
        :ordered-songs="orderedSongs"
        :selected-instrument="selectedInstrument"
        list-class="navbar-nav pe-5"
        collapse-id-prefix="dropdown"
      />
    </div>

    <!-- Footer area (always show when sidebar is open) -->
    <div v-show="!isSidebarCollapsed" class="mt-auto">
      <!-- Song actions (only show when viewing a song) -->
      <div v-if="currentSong" class="pt-3 pb-3">
        <SongActionButtons
          :current-song="currentSong"
          download-modal-id="#downloadModal"
          @watch-on-you-tube="watchOnYouTube"
        />
      </div>

      <!-- Review Mode Toggle -->
      <div class="pt-3 pb-3" :class="{ 'border-top': currentSong }">
        <UnderReviewToggle
          toggle-id="underReviewToggle"
          v-model:under-review-view-enabled="songsStore.underReviewViewEnabled"
        />
      </div>
    </div>

    <!-- Advanced Filter Modal-->
    <FilterModal class="modal" id="filterModal" />

    <!-- Download Modal -->
    <DownloadModal :song="currentSong" :current-instrument="currentInstrument" />
  </nav>
</template>
