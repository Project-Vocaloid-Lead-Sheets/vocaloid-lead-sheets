<script setup lang="ts">
/** The navbar is for smaller displays that display the song list as a dropdown from the top.
 * Its counterpart is the sidebar. */
import { computed, Teleport } from 'vue'
import { useSongFilters } from '@/scripts/useSongFilters'
import { useSongActions } from '@/scripts/useSongActions'
import { useSongsStore } from '@/stores/songs'
import FilterModal from '@/components/FilterModal.vue'
import DownloadModal from '@/components/DownloadModal.vue'
import InstrumentButtons from '@/components/shared/InstrumentButtons.vue'
import SearchBar from '@/components/shared/SearchBar.vue'
import ActionButtons from '@/components/shared/ActionButtons.vue'
import GroupSortControls from '@/components/shared/GroupSortControls.vue'
import UnderReviewToggle from '@/components/shared/UnderReviewToggle.vue'
import SongActionButtons from '@/components/shared/SongActionButtons.vue'
import SongList from '@/components/shared/SongList.vue'
import TvSizeToggle from '@/components/shared/TvSizeToggle.vue'

const songsStore = useSongsStore()

const {
  instruments,
  selectedInstrument,
  searchQuery,
  groupBy,
  sortBy,
  resetSearch,
  toggleFilterModal,
  toggleGroupsCollapsed,
  areGroupsCollapsed,
  orderedSongs,
  pickRandomSong,
  selectedLabels,
  selectedProducers,
  selectedSingers,
  dateRange,
  useTvSize,
} = useSongFilters()

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
    dateRange.value.end !== ''
  )
})
</script>

<!-- Uses the collapsible navbar offcanvas example from Bootstrap documentation -->
<template>
  <nav class="navbar navbar-dark fixed-top d-lg-none" style="background-color: #206071">
    <div class="container-fluid">
      <button
        class="navbar-toggler"
        type="button"
        data-bs-toggle="offcanvas"
        data-bs-target="#offcanvasNavbar"
        aria-controls="offcanvasNavbar"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>
      <RouterLink class="navbar-brand" to="/">Project VocaLead Sheets</RouterLink>

      <div
        class="offcanvas offcanvas-top h-75"
        tabindex="-1"
        id="offcanvasNavbar"
        aria-labelledby="offcanvasNavbarLabel"
        style="background-color: #206071; color: #fff"
      >
        <div class="offcanvas-header">
          <button
            type="button"
            class="btn-close btn-close-white ms-0 me-auto"
            data-bs-dismiss="offcanvas"
            aria-label="Close"
          ></button>
          <h5 class="offcanvas-title" id="offcanvasNavbarLabel">Project VocaLead Sheets</h5>
        </div>
        <div class="offcanvas-body d-flex flex-column p-0">
          <div class="flex-grow-1 overflow-auto p-3">
            <!-- Instrument Buttons -->
            <InstrumentButtons
              :instruments="instruments"
              v-model:selected-instrument="selectedInstrument"
              wrapper-class="mb-3 w-100"
            />

            <!-- Search -->
            <SearchBar
              v-model:search-query="searchQuery"
              @reset="resetSearch"
              placeholder="Search"
              class="mb-3"
            />

            <!-- Action Buttons -->
            <ActionButtons
              :has-active-filters="hasActiveFilters"
              :are-groups-collapsed="areGroupsCollapsed"
              filter-modal-id="#navbarFilterModal"
              @shuffle="pickRandomSong"
              @toggle-collapse="toggleGroupsCollapsed"
              class="mb-3"
            />

            <!-- Grouping & Sorting -->
            <div class="mb-4">
              <GroupSortControls v-model:group-by="groupBy" v-model:sort-by="sortBy" />
            </div>

            <!-- Song List -->
            <SongList
              :ordered-songs="orderedSongs"
              :selected-instrument="selectedInstrument"
              collapse-id-prefix="collapse"
            />
          </div>

                <TvSizeToggle :current-song="currentSong" v-model:use-tv-size="useTvSize" />
            <UnderReviewToggle
              toggle-id="navbarUnderReviewToggle"
              v-model:under-review-view-enabled="songsStore.underReviewViewEnabled"
            />
          </div>

          <!-- Footer with actions (only show when viewing a song) -->
          <div
            v-if="currentSong"
            class="border-top p-3"
            style="background-color: #206071; color: #fff"
          >
            <SongActionButtons
              :current-song="currentSong"
              download-modal-id="#navbarDownloadModal"
              download-label-class="d-none d-sm-inline ms-1"
              youtube-label-class="d-none d-sm-inline ms-1"
              @watch-on-you-tube="watchOnYouTube"
            />
          </div>
        </div>
      </div>
    </div>
  </nav>

  <!-- Advanced Filter Modal (teleported to body to avoid z-index issues) -->
  <Teleport to="body">
    <FilterModal class="modal" id="navbarFilterModal" />
  </Teleport>

  <!-- Download Modal (teleported to body to avoid z-index issues) -->
  <Teleport to="body">
    <DownloadModal
      :song="currentSong"
      :current-instrument="currentInstrument"
      id="navbarDownloadModal"
    />
  </Teleport>
</template>
