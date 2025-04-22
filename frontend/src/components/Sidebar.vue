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

<template>
  <nav id="sidebar" class="bg-dark text-light h-100 pt-2 px-3">
    <!-- Sidebar Fixed Area -->
    <div class="d-flex flex-column mb-2">
      <!-- Sidebar Header -->
      <div class="d-flex flex-row mb-2">
        <a
          href="#"
          data-bs-target=".sidebar-nav-collapsible"
          data-bs-toggle="collapse"
          class="text-decoration-none"
          ><i class="bi bi-list"></i>
        </a>
        <span class="sidebar-nav-collapsible collapse collapse-horizontal ms-auto"
          ><RouterLink class="navbar-brand" to="/">Project Vocaloid Lead Sheets</RouterLink>
        </span>
      </div>
      <!-- Sidebar Body -->
      <div class="sidebar-nav-collapsible collapse collapse-horizontal">
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
              <input type="text" class="form-control" placeholder="Search" v-model="searchQuery" />
              <button class="btn btn-outline-light" type="button" @click="resetSearch">
                <i class="bi bi-arrow-clockwise"></i>
              </button>
            </div>
            <button class="btn btn-sm btn-outline-light me-2" @click="toggleFilterModal">
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
      class="sidebar-nav-collapsible collapse collapse-horizontal overflow-auto"
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
  </nav>
</template>
