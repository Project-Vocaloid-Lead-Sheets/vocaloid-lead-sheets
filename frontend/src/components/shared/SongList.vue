<template>
  <ul :class="listClass">
    <li class="nav-item group" v-for="(group, index) in orderedSongs" :key="group.groupName">
      <button
        :id="collapseIdPrefix + index"
        class="nav-link fw-bold"
        data-bs-toggle="collapse"
        :data-bs-target="'#' + collapseIdPrefix + 'collapse' + index"
      >
        {{ group.groupName }}
      </button>
      <ul
        class="song collapse show list-unstyled small"
        :id="collapseIdPrefix + 'collapse' + index"
      >
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
</template>

<script setup lang="ts">
import type { Instrument, Song } from '@/types/types'
import { useSongsStore } from '@/stores/songs'
import { generateSongSlug } from '@/utils/slugUtils'

interface GroupedSongs {
  groupName: string
  songs: Song[]
}

interface Props {
  orderedSongs: GroupedSongs[]
  selectedInstrument: Instrument
  listClass?: string
  collapseIdPrefix?: string
}

withDefaults(defineProps<Props>(), {
  listClass: 'navbar-nav',
  collapseIdPrefix: '',
})

const songsStore = useSongsStore()
</script>
