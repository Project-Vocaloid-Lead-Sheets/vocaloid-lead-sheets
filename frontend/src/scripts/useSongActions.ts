import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { Song, Instrument } from '@/types/types'
import { useSongsStore } from '@/stores/songs'

export const useSongActions = () => {
  const route = useRoute()
  const songsStore = useSongsStore()

  // Get current song based on route
  const currentSong = computed<Song | null>(() => {
    const songSlug = route.params.songSlug as string
    if (!songSlug) return null
    return songsStore.getSongBySlug(songSlug) || null
  })

  const currentInstrument = computed(() => {
    const transposition = route.query.transposition
    return typeof transposition === 'string' ? (transposition as Instrument) : 'C'
  })

  return {
    currentSong,
    currentInstrument,
  }
}
