<script setup lang="ts">
/** The sidebar is for larger displays that can fit the song select list on the side.
 * Its counterpart is the navbar.*/

import { computed } from 'vue'
import { useSongFilters } from '@/scripts/useSongFilters'
import { useSongActions } from '@/scripts/useSongActions'
import FilterModal from '@/components/FilterModal.vue'
import DownloadModal from '@/components/DownloadModal.vue'

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

const { currentSong, currentInstrument, printPdf, watchOnYouTube } = useSongActions()

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
  <nav id="sidebar" class="bg-dark text-light h-100 pt-2 px-3 d-flex flex-column">
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
          ><RouterLink class="navbar-brand" to="/">Project Vocaloid Lead Sheets</RouterLink>
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
                <option value="a-z">A-Z</option>
                <option value="z-a">Z-A</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Sidebar Scrollable Area -->
    <div
      id="sidebar-nav"
      class="sidebar-nav-collapsible collapse collapse-horizontal overflow-auto flex-grow-1"
      style="max-height: calc(100vh - 10.5rem)"
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
                class="nav-link"
                :to="{
                  name: 'sheetView',
                  params: {
                    songSlug: song.title.toLowerCase().replace(/\s+/g, '-'),
                  },
                  query: {
                    instrument: selectedInstrument,
                  },
                }"
              >
                {{ song.title }}
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>
    </div>

    <!-- Footer with actions (only show when viewing a song) -->
    <div v-if="currentSong && !isSidebarCollapsed" class="mt-auto pt-3 pb-3">
      <div class="text-center mb-2">
        <small class="text-muted">{{ currentSong.title }}</small>
      </div>
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

    <!-- Advanced Filter Modal-->
    <FilterModal class="modal" id="filterModal" />

    <!-- Download Modal -->
    <DownloadModal :song="currentSong" :current-instrument="currentInstrument" />
  </nav>
</template>
