<script setup lang="ts">
import { useSongFilters } from '@/scripts/useSongFilters'

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
} = useSongFilters()
</script>

<!-- Uses the collapsible navbar offcanvas example from Bootstrap documentation -->
<template>
  <nav class="navbar navbar-dark bg-dark fixed-top d-lg-none">
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
      <RouterLink class="navbar-brand" to="/">Project Vocaloid Lead Sheets</RouterLink>

      <div
        class="offcanvas offcanvas-top text-bg-dark h-75"
        tabindex="-1"
        id="offcanvasNavbar"
        aria-labelledby="offcanvasNavbarLabel"
      >
        <div class="offcanvas-header">
          <button
            type="button"
            class="btn-close btn-close-white ms-0 me-auto"
            data-bs-dismiss="offcanvas"
            aria-label="Close"
          ></button>
          <h5 class="offcanvas-title" id="offcanvasNavbarLabel">Project Vocaloid Lead Sheets</h5>
        </div>
        <div class="offcanvas-body">
          <!-- Instrument Buttons -->
          <div class="btn-group flex-wrap mb-3 w-100">
            <button
              v-for="instrument in instruments"
              :key="instrument"
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

          <!-- Search -->
          <div class="input-group input-group-sm mb-3">
            <input type="text" class="form-control" placeholder="Search" v-model="searchQuery" />
            <button class="btn btn-outline-light" type="button" @click="resetSearch">
              <i class="bi bi-arrow-clockwise"></i>
            </button>
          </div>

          <!-- Action Buttons -->
          <div class="d-flex gap-2 mb-3">
            <button class="btn btn-sm btn-outline-light" @click="toggleFilterModal">
              <i class="bi bi-filter"></i>
            </button>
            <button class="btn btn-sm btn-outline-light" @click="pickRandomSong">
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

          <!-- Grouping & Sorting -->
          <div class="input-group input-group-sm mb-2">
            <span class="input-group-text"><i class="bi bi-folder"></i></span>
            <select class="form-select" v-model="groupBy">
              <option value="none">None</option>
              <option value="singer">Singer</option>
              <option value="producer">Producer</option>
            </select>
          </div>
          <div class="input-group input-group-sm mb-4">
            <span class="input-group-text"><i class="bi bi-sort-alpha-down"></i></span>
            <select class="form-select" v-model="sortBy">
              <option value="a-z">A-Z</option>
              <option value="z-a">Z-A</option>
            </select>
          </div>

          <!-- Song List -->
          <ul class="navbar-nav">
            <li
              class="nav-item group"
              v-for="(group, index) in orderedSongs"
              :key="group.groupName"
            >
              <button
                class="nav-link fw-bold"
                :data-bs-target="'#collapse' + index"
                data-bs-toggle="collapse"
              >
                {{ group.groupName }}
              </button>
              <ul class="collapse show list-unstyled small song" :id="'collapse' + index">
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
      </div>
    </div>
  </nav>
</template>
