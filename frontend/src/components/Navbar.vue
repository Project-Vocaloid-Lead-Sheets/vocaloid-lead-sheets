<script setup lang="ts">
/** The navbar is for smaller displays that display the song list as a dropdown from the top.
 * Its counterpart is the sidebar. */
import { computed, onMounted, onUnmounted, ref, Teleport } from 'vue'
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

const { currentSong, currentInstrument } = useSongActions()

const downloadModalRef = ref<InstanceType<typeof DownloadModal>>()

const startDownloadFlow = () => {
  downloadModalRef.value?.startDownloadFlow()
}

const handleOpenDownloadModalEvent = () => {
  if (typeof window !== 'undefined' && window.innerWidth >= 992) return
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
onMounted(() => {
  window.addEventListener(OPEN_DOWNLOAD_MODAL_EVENT, handleOpenDownloadModalEvent)
})

onUnmounted(() => {
  window.removeEventListener(OPEN_DOWNLOAD_MODAL_EVENT, handleOpenDownloadModalEvent)
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
        <div class="offcanvas-header pb-2">
          <button
            type="button"
            class="btn-close btn-close-white ms-0 me-auto"
            data-bs-dismiss="offcanvas"
            aria-label="Close"
          ></button>
          <h5 class="offcanvas-title" id="offcanvasNavbarLabel">
            <RouterLink class="navbar-brand m-0" to="/">Project VocaLead Sheets</RouterLink>
          </h5>
        </div>
        <div class="offcanvas-body d-flex flex-column p-0">
          <div
            class="px-3 pb-3 pt-2 border-bottom navbar-filter-controls"
            style="background-color: #206071; color: #fff"
          >
            <SongFilterControls
              :instruments="instruments"
              :has-active-filters="hasActiveFilters"
              :are-groups-collapsed="areGroupsCollapsed"
              filter-modal-id="#navbarFilterModal"
              :show-active-filters="true"
              :selected-labels="selectedLabels"
              :selected-producers="selectedProducers"
              :selected-singers="selectedSingers"
              :date-range="dateRange"
              v-model:selected-instrument="selectedInstrument"
              v-model:search-query="searchQuery"
              v-model:group-by="groupBy"
              v-model:sort-by="sortBy"
              @reset="resetSearch"
              @shuffle="pickRandomSong"
              @toggle-collapse="toggleGroupsCollapsed"
            />
            </div>

          <div class="flex-grow-1 overflow-auto p-3">
            <!-- Song List -->
            <SongList
              :ordered-songs="orderedSongs"
              :selected-instrument="selectedInstrument"
              collapse-id-prefix="collapse"
            />
          </div>

          <div class="mt-auto px-3" style="background-color: #1a5064; color: #fff">
            <BottomFooter
              :show-top="Boolean(currentSong) && hasTvSizeForCurrentSong"
              :show-bottom="true"
            >
              <template #top>
                <TvSizeToggle :current-song="currentSong" v-model:use-tv-size="useTvSize" />
              </template>

              <template #bottom>
            <UnderReviewToggle
              toggle-id="navbarUnderReviewToggle"
              v-model:under-review-view-enabled="songsStore.underReviewViewEnabled"
            />
              </template>
            </BottomFooter>
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
      ref="downloadModalRef"
      :song="currentSong"
      :current-instrument="currentInstrument"
      :use-tv-size="useTvSize"
      id="navbarDownloadModal"
    />
  </Teleport>
</template>

<style scoped>
.navbar-filter-controls {
  position: relative;
  z-index: 2;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
}
</style>
