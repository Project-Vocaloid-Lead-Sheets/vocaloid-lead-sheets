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
        <li
          class="nav-item d-flex align-items-center"
          v-for="song in group.songs"
          :key="song.title"
        >
          <RouterLink
            class="nav-link d-flex align-items-center"
            :to="{
              name: 'sheetView',
              params: {
                songSlug: generateSongSlug(song.title),
              },
              query: {
                instrument: selectedInstrument,
                tv_size: route.query.tv_size,
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

          <a
            v-if="isSelectedSong(song) && song.videoLinks?.YouTube"
            :href="song.videoLinks.YouTube"
            class="ms-2"
            style="color: inherit"
            target="_blank"
            rel="noopener noreferrer"
            title="Watch on YouTube"
            aria-label="Watch on YouTube"
          >
            <i class="bi bi-youtube"></i>
          </a>
        </li>
      </ul>
    </li>
  </ul>
</template>

<script setup lang="ts">
import type { Instrument, Song } from '@/types/types'
import { useSongsStore } from '@/stores/songs'
import { generateSongSlug } from '@/utils/slugUtils'
import { useRoute } from 'vue-router'

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
const route = useRoute()

const isSelectedSong = (song: Song) => {
  const currentSlug = route.params.songSlug as string | undefined
  if (!currentSlug) return false
  return generateSongSlug(song.title) === currentSlug
}
</script>
