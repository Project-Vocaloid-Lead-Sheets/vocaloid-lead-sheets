<style scoped>
/* Make the sidebar hamburger menu icon white */
.bi-list {
  color: #fff !important;
}

/* Ensure toggle switch is visible on dark background */
.form-switch .form-check-input {
  background-color: #6c757d;
  border-color: #6c757d;
}

.form-switch .form-check-input:checked {
  background-color: #0d6efd;
  border-color: #0d6efd;
}

.form-switch .form-check-input:focus {
  box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
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
import { generateSongSlug } from '@/utils/slugUtils'

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
        <div v-if="hasActiveFilters" class="mb-2 p-2 bg-white text-dark rounded small border">
          <strong>Active Filters:</strong>
          <div v-if="selectedLabels.length > 0">Labels: {{ selectedLabels.join(', ') }}</div>
          <div v-if="selectedProducers.length > 0">
            Producers: {{ selectedProducers.join(', ') }}
          </div>
          <div v-if="selectedSingers.length > 0">Singers: {{ selectedSingers.join(', ') }}</div>
          <div v-if="dateRange.start || dateRange.end">
            Date: {{ dateRange.start || '...' }} to {{ dateRange.end || '...' }}
          </div>
        </div>
        <!-- Search Component -->
        <div class="d-flex flex-column gap-2">
          <!-- Row 1: Instrument/Transposition Buttons -->
          <div class="d-flex flex-row flex-wrap btn-group" role="group">
            <button
              v-for="instrument in instruments"
              :key="instrument"
              aria-label="Instruments"
              type="button"
              :class="
                instrument === selectedInstrument
                  ? 'btn btn-sm btn-light'
                  : 'btn btn-sm btn-outline-light'
              "
              @click="selectedInstrument = instrument"
            >
              {{ instrument }}
            </button>
          </div>
          <!-- Row 2: Search Field + Navigation Buttons -->
          <div class="d-flex">
            <div class="input-group input-group-sm me-2">
              <input
                type="text"
                class="form-control"
                placeholder="Search by name"
                v-model="searchQuery"
              />
              <button class="btn btn-outline-light" type="button" @click="resetSearch">
                <i class="bi bi-arrow-clockwise"></i>
              </button>
            </div>
            <button
              type="button"
              :class="
                hasActiveFilters ? 'btn btn-sm btn-light me-2' : 'btn btn-sm btn-outline-light me-2'
              "
              data-bs-toggle="modal"
              data-bs-target="#filterModal"
            >
              <i class="bi bi-filter"></i>
            </button>
            <button class="btn btn-sm btn-outline-light me-2" @click="pickRandomSong">
              <i class="bi bi-shuffle"></i>
            </button>
            <button
              class="btn btn-sm btn-outline-light"
              :data-bs-target="areGroupsCollapsed ? '.song.collapse.show' : '.song.collapse'"
              data-bs-toggle="collapse"
              @click="toggleGroupsCollapsed"
            >
              <i class="bi bi-chevron-expand"></i>
            </button>
          </div>

          <!-- Row 3: Group + Sort Selects -->
          <div class="d-flex gap-2 align-items-center">
            <div class="input-group">
              <span class="input-group-text" id="basic-addon1"
                ><i class="bi bi-folder small"></i
              ></span>
              <select id="group-select" class="form-select form-select-sm" v-model="groupBy">
                <option value="none">None</option>
                <option value="singer">Singer</option>
                <option value="producer">Producer</option>
              </select>
            </div>
            <div class="input-group">
              <span class="input-group-text" id="basic-addon1">
                <i class="bi bi-sort-alpha-down small"></i
              ></span>
              <select id="sort-select" class="form-select form-select-sm" v-model="sortBy">
                <option value="title-asc">Title: A → Z</option>
                <option value="title-desc">Title: Z → A</option>
                <option value="bpm-asc">BPM: Low → High</option>
                <option value="bpm-desc">BPM: High → Low</option>
                <option value="date-asc">Release Date: Old → New</option>
                <option value="date-desc">Release Date: New → Old</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Sidebar Scrollable Area -->
    <div
      id="sidebar-nav"
      class="sidebar-nav-collapsible collapse collapse-horizontal overflow-auto"
      style="flex: 1 1 0; min-height: 0"
    >
      <ul id="song-list" class="navbar-nav pe-5">
        <li class="nav-item group" v-for="(group, index) in orderedSongs" :key="group.groupName">
          <button
            :id="'dropdown' + index"
            class="nav-link fw-bold"
            data-bs-toggle="collapse"
            :data-bs-target="'#' + index + 'collapse'"
          >
            {{ group.groupName }}
          </button>
          <ul class="song collapse show list-unstyled small" :id="index + 'collapse'">
            <li class="nav-item" v-for="song in group.songs" :key="song.title">
              <RouterLink
                class="nav-link d-flex align-items-center"
                :to="{
                  name: 'sheetView',
                  params: {
                    songSlug: generateSongSlug(song.title),
                  },
                  query: {
                    instrument: selectedInstrument,
                  },
                }"
              >
                <span>{{ song.title }}</span>
                <span
                  v-if="songsStore.isUnderReviewSong(song)"
                  class="badge bg-light text-dark ms-2 small"
                >
                  Under Review
                </span>
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>
    </div>

    <!-- Footer area (always show when sidebar is open) -->
    <div v-show="!isSidebarCollapsed" class="mt-auto">
      <!-- Song actions (only show when viewing a song) -->
      <div v-if="currentSong" class="pt-3 pb-3">
        <div class="btn-group w-100" role="group" aria-label="Song actions">
          <button
            type="button"
            class="btn btn-outline-light btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#downloadModal"
            :disabled="!currentSong"
            title="Download PDF"
          >
            <i class="bi bi-download"></i>
            <span class="d-none d-xl-inline ms-1">Download</span>
          </button>
          <!-- Print button hidden for now
          <button
            type="button"
            class="btn btn-outline-light btn-sm"
            @click="printPdf"
            :disabled="!currentSong.pdfs[currentInstrument] && !currentSong.pdfs['C']"
            title="Print PDF"
          >
            <i class="bi bi-printer"></i>
            <span class="d-none d-xl-inline ms-1">Print</span>
          </button>
          -->
          <button
            type="button"
            class="btn btn-outline-light btn-sm"
            @click="watchOnYouTube"
            :disabled="!currentSong.videoLinks?.YouTube"
            title="Watch on YouTube"
          >
            <i class="bi bi-youtube"></i>
            <span class="d-none d-xl-inline ms-1">YouTube</span>
          </button>
        </div>
      </div>

      <!-- Review Mode Toggle -->
      <div class="pt-3 pb-3" :class="{ 'border-top': currentSong }">
        <div class="form-check form-switch">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="underReviewToggle"
            v-model="songsStore.underReviewViewEnabled"
          />
          <label class="form-check-label text-light small" for="underReviewToggle">
            Show sheets currently under review
          </label>
        </div>
      </div>
    </div>

    <!-- Advanced Filter Modal-->
    <FilterModal class="modal" id="filterModal" />

    <!-- Download Modal -->
    <DownloadModal :song="currentSong" :current-instrument="currentInstrument" />
  </nav>
</template>
