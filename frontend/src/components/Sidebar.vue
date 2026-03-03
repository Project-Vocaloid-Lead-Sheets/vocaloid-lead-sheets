<style scoped>
/* Make the sidebar hamburger menu icon white */
.bi-list {
  color: #fff !important;
}
</style>
<script setup lang="ts">
/** The sidebar is for larger displays that can fit the song select list on the side.
 * Its counterpart is the navbar.*/

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useSongFilters } from '@/scripts/useSongFilters'
import { useSongActions } from '@/scripts/useSongActions'
import { useSongsStore } from '@/stores/songs'
import FilterModal from '@/components/FilterModal.vue'
import DownloadModal from '@/components/DownloadModal.vue'
import SongFilterControls from '@/components/shared/SongFilterControls.vue'
import UnderReviewToggle from '@/components/shared/UnderReviewToggle.vue'
import SongList from '@/components/shared/SongList.vue'
import TvSizeToggle from '@/components/shared/TvSizeToggle.vue'
import BottomFooter from '@/components/shared/BottomFooter.vue'
import { OPEN_DOWNLOAD_MODAL_EVENT } from '@/utils/downloadEvents'

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
  lengthRange,
  toggleSidebarCollapsed,
  isSidebarCollapsed,
  useTvSize,
} = useSongFilters()

const { currentSong, currentInstrument } = useSongActions()

const downloadModalRef = ref<InstanceType<typeof DownloadModal>>()

const startDownloadFlow = () => {
  downloadModalRef.value?.startDownloadFlow()
}

const handleOpenDownloadModalEvent = () => {
  if (typeof window !== 'undefined' && window.innerWidth < 992) return
  startDownloadFlow()
}

const hasTvSizeForCurrentSong = computed(() => {
  const tvSizePdfs = currentSong.value?.pdfsTvSize
  if (!tvSizePdfs) return false
  return Object.keys(tvSizePdfs).length > 0
})

// Computed property to check if any advanced filters are active and should be displayed
const hasActiveFilters = computed(() => {
  return (
    selectedLabels.value.length > 0 ||
    selectedProducers.value.length > 0 ||
    selectedSingers.value.length > 0 ||
    dateRange.value.start !== '' ||
    dateRange.value.end !== '' ||
    lengthRange.value.min !== null ||
    lengthRange.value.max !== null
  )
})

onMounted(() => {
  window.addEventListener(OPEN_DOWNLOAD_MODAL_EVENT, handleOpenDownloadModalEvent)
})

onUnmounted(() => {
  window.removeEventListener(OPEN_DOWNLOAD_MODAL_EVENT, handleOpenDownloadModalEvent)
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
        <SongFilterControls
          :instruments="instruments"
          :has-active-filters="hasActiveFilters"
          :are-groups-collapsed="areGroupsCollapsed"
          filter-modal-id="#filterModal"
          :show-active-filters="true"
          :selected-labels="selectedLabels"
          :selected-producers="selectedProducers"
          :selected-singers="selectedSingers"
          :date-range="dateRange"
          :length-range="lengthRange"
          v-model:selected-instrument="selectedInstrument"
          v-model:search-query="searchQuery"
          v-model:group-by="groupBy"
          v-model:sort-by="sortBy"
          @reset="resetSearch"
          @shuffle="pickRandomSong"
          @toggle-collapse="toggleGroupsCollapsed"
        />
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
      <BottomFooter :show-top="hasTvSizeForCurrentSong" :show-bottom="true">
        <template #top>
          <TvSizeToggle :current-song="currentSong" v-model:use-tv-size="useTvSize" />
        </template>

        <template #bottom>
          <UnderReviewToggle
            toggle-id="underReviewToggle"
            v-model:under-review-view-enabled="songsStore.underReviewViewEnabled"
          />
        </template>
      </BottomFooter>
    </div>

    <!-- Advanced Filter Modal-->
    <FilterModal class="modal" id="filterModal" />

    <!-- Download Modal -->
    <DownloadModal
      ref="downloadModalRef"
      :song="currentSong"
      :current-instrument="currentInstrument"
      :use-tv-size="useTvSize"
      id="downloadModal"
    />
  </nav>
</template>
